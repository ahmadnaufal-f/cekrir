from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cekrir.config import Settings
from cekrir.db.session import get_session
from cekrir.dependencies import get_provider, get_publisher, get_user_id
from cekrir.middleware import RequirePermission
from cekrir.routers.auth import router as auth_router
from cekrir.routers.detections import camera_router
from cekrir.routers.payments import router as payments_router
from cekrir.routers.shipments import router as shipments_router
from cekrir.schemas import CameraFrameResult, FrameDetection
from cekrir.services.detections import ingest_esp_frame, ingest_frame
from cekrir.services.payments import IdempotencyConflict
from cekrir.validation.shipments import CameraCourierInput, CameraFrameInput


def client_for(router):
    app = FastAPI()
    app.include_router(router)
    override_permissions(app, router)
    app.dependency_overrides[get_session] = lambda: object()
    app.dependency_overrides[get_provider] = lambda: object()
    app.dependency_overrides[get_publisher] = lambda: object()
    return TestClient(app)


def override_permissions(app, router):
    for route in router.routes:
        for dependency in getattr(route, "dependencies", []):
            if isinstance(dependency.dependency, RequirePermission):
                app.dependency_overrides[dependency.dependency] = lambda: None


def test_invalid_shipment_is_rejected_before_service():
    client = client_for(shipments_router)
    with patch("cekrir.services.shipments.submit_shipment") as service:
        response = client.post(
            "/api/v1/shipments", json={"resi_number": "https://bad", "courier": "jne"}
        )
    assert response.status_code == 422
    service.assert_not_called()


def test_camera_request_is_validated_before_service():
    client = client_for(camera_router)
    with patch(
        "cekrir.services.detections.ingest_frame", return_value=CameraFrameResult()
    ) as service:
        params = {"courier": "jne", "camera_id": "door"}
        assert (
            client.post(
                "/api/v1/detections/frame",
                params=params,
                content=b"jpeg",
                headers={"content-type": "image/png"},
            ).status_code
            == 415
        )
        service.assert_not_called()
        assert (
            client.post(
                "/api/v1/detections/frame",
                params=params,
                content=b"jpeg",
                headers={"content-type": "image/jpeg"},
            ).status_code
            == 200
        )
        service.assert_called_once()


def test_frame_service_does_not_register_ambiguous_codes():
    metadata = CameraFrameInput(courier="jne", camera_id="door")
    publisher = Mock()
    with (
        patch("cekrir.services.detections.decode_frame", return_value=["ABC123", "DEF456"]),
        patch("cekrir.services.detections.register_shipment") as submit,
    ):
        result = ingest_frame(b"jpeg", metadata, Mock(), Mock(), publisher)
    assert result.ambiguous and result.detected_count == 0
    submit.assert_not_called()


def test_esp_frame_limits_tracking_response_to_status():
    frame = CameraFrameResult(
        detected_count=1,
        detections=[
            FrameDetection(
                resi_number="ABC123",
                shipment_id=uuid4(),
                created=True,
                tracking={"summary": {"status": "DELIVERED"}, "detail": {"address": "private"}},
            )
        ],
    )
    with patch("cekrir.services.detections.ingest_frame", return_value=frame):
        result = ingest_esp_frame(b"jpeg", "device", CameraCourierInput(), Mock(), Mock(), Mock())
    assert result.detections[0].tracking == {"summary": {"status": "DELIVERED"}}


def test_registration_validation_runs_before_service():
    app = FastAPI()
    app.state.settings = Settings(_env_file=None)
    app.include_router(auth_router)
    app.dependency_overrides[get_session] = lambda: object()
    with patch("cekrir.services.accounts.register_account") as service:
        response = TestClient(app).post(
            "/api/v1/auth/register",
            json={
                "email": "invalid",
                "full_name": "Person",
                "password": "a sufficiently long password",
            },
        )
    assert response.status_code == 422
    service.assert_not_called()


def test_payment_service_conflict_is_mapped_to_http_409():
    app = FastAPI()
    app.include_router(payments_router)
    override_permissions(app, payments_router)
    app.dependency_overrides[get_session] = lambda: object()
    app.dependency_overrides[get_user_id] = lambda: "test-user"
    with patch(
        "cekrir.services.payments.submit_payment", side_effect=IdempotencyConflict("conflict")
    ):
        response = TestClient(app).post(
            "/api/v1/payments",
            json={"reference": "order-1", "amount": 10000},
            headers={"Idempotency-Key": "key-1"},
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "conflict"
