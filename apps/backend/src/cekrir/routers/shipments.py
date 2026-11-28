from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.dependencies import get_provider, get_publisher, get_user_id
from cekrir.middleware import RequirePermission
from cekrir.schemas import PackageRead, ShipmentRead, VisibleShipment
from cekrir.services import binderbyte, screenshot_analysis, shipments
from cekrir.services.cctv_photos import photo_path
from cekrir.services.notifications import NotificationPublisher
from cekrir.services.tracking import TrackingProvider
from cekrir.validation.screenshots import SCREENSHOT_FORMATS, read_screenshot
from cekrir.validation.shipments import ExpectedPackageInput, ResiInput
from cekrir.validation.tracking import BinderByteInput

router = APIRouter(prefix="/api/v1", tags=["shipments"])


@router.post(
    "/shipments/analyze-screenshot",
    response_model=screenshot_analysis.ScreenshotAnalysis,
    dependencies=[Depends(RequirePermission("shipments:create"))],
    responses={
        413: {"description": "Screenshot exceeds 5 MiB"},
        415: {"description": "Unsupported screenshot type"},
        422: {"description": "Invalid screenshot image"},
        502: {"description": "Invalid screenshot analysis response"},
        503: {"description": "Screenshot analysis unavailable"},
        504: {"description": "Screenshot analysis timed out"},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                media_type: {"schema": {"type": "string", "format": "binary"}}
                for media_type in SCREENSHOT_FORMATS
            },
        }
    },
)
async def analyze_screenshot(request: Request, response: Response):
    image, media_type = await read_screenshot(request)
    try:
        result = await screenshot_analysis.analyze(request.app.state.settings, image, media_type)
    except screenshot_analysis.AnalysisUnavailable as exc:
        raise HTTPException(503, "Screenshot analysis unavailable") from exc
    except screenshot_analysis.AnalysisTimeout as exc:
        raise HTTPException(504, "Screenshot analysis timed out") from exc
    except screenshot_analysis.InvalidAnalysis as exc:
        raise HTTPException(502, "Invalid screenshot analysis response") from exc
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/tracking/binderbyte", dependencies=[Depends(RequirePermission("shipments:read"))])
def check_binderbyte(payload: BinderByteInput, request: Request):
    try:
        return binderbyte.check_tracking(request.app.state.settings, payload)
    except binderbyte.BinderByteUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/shipments",
    response_model=list[VisibleShipment],
    dependencies=[Depends(RequirePermission("shipments:read"))],
)
def list_shipments(
    response: Response,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    response.headers["Cache-Control"] = "private, no-store"
    return shipments.list_shipments(session, user_id, limit, offset)


@router.post(
    "/shipments/expected",
    response_model=PackageRead,
    status_code=201,
    dependencies=[Depends(RequirePermission("shipments:create"))],
    responses={200: {"model": PackageRead}, 409: {"description": "Receiving location unavailable"}},
)
def add_expected_package(
    payload: ExpectedPackageInput,
    response: Response,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        package, created = shipments.add_expected_package(session, user_id, payload)
    except shipments.ShipmentLocationUnavailable as exc:
        raise HTTPException(409, str(exc)) from exc
    response.status_code = 201 if created else 200
    response.headers["Cache-Control"] = "private, no-store"
    return package


@router.get(
    "/shipments/{shipment_id}",
    response_model=VisibleShipment,
    dependencies=[Depends(RequirePermission("shipments:read"))],
)
def get_shipment(
    shipment_id: UUID,
    response: Response,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        shipment = shipments.get_shipment(session, str(shipment_id), user_id)
    except shipments.ShipmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response.headers["Cache-Control"] = "private, no-store"
    return shipment


@router.get(
    "/shipments/{shipment_id}/photo",
    dependencies=[Depends(RequirePermission("shipments:read"))],
)
def get_shipment_photo(
    shipment_id: UUID,
    request: Request,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        shipment = shipments.get_shipment(session, str(shipment_id), user_id)
    except shipments.ShipmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if shipment.photo_status == "pending":
        raise HTTPException(status_code=409, detail="Photo capture is pending")
    if shipment.photo_status != "ready":
        raise HTTPException(status_code=404, detail="Photo is unavailable")
    path = photo_path(request.app.state.settings.cctv_photo_dir, shipment_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Photo is unavailable")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/shipments",
    response_model=ShipmentRead,
    status_code=201,
    dependencies=[Depends(RequirePermission("shipments:create"))],
)
def create_shipment(
    payload: ResiInput,
    response: Response,
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    shipment, created = shipments.submit_shipment(session, payload, provider, publisher)
    response.status_code = 201 if created else 200
    return shipment


@router.post(
    "/shipments/{shipment_id}/refresh",
    response_model=VisibleShipment,
    dependencies=[Depends(RequirePermission("shipments:refresh"))],
)
def check_shipment(
    shipment_id: str,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
    provider: TrackingProvider = Depends(get_provider),
    publisher: NotificationPublisher = Depends(get_publisher),
):
    try:
        return shipments.check_shipment(session, shipment_id, user_id, provider, publisher)
    except shipments.ShipmentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
