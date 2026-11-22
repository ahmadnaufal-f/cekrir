from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.dependencies import get_user_id
from cekrir.middleware import RequirePermission
from cekrir.schemas import NotificationRead
from cekrir.services import email_notifications, notifications, push_notifications
from cekrir.services.email import EmailUnavailable
from cekrir.validation.devices import FcmRegistration, FcmUnregister
from cekrir.validation.notifications import EmailNotificationInput
from cekrir.validation.payments import IdempotencyKey

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.post(
    "/notifications/fcm/unregister", dependencies=[Depends(RequirePermission("notifications:read"))]
)
def unregister_fcm_token(
    payload: FcmUnregister,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    push_notifications.unregister_by_token(session, user_id, payload.token.get_secret_value())
    return {"detail": "Push device removed"}


@router.post("/notifications/fcm", dependencies=[Depends(RequirePermission("notifications:read"))])
def register_fcm(
    payload: FcmRegistration,
    user_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        return push_notifications.register_token(session, user_id, payload)
    except push_notifications.PushLocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except push_notifications.PushTokenConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete(
    "/notifications/fcm/{device_id}",
    dependencies=[Depends(RequirePermission("notifications:read"))],
)
def unregister_fcm(
    device_id: UUID, user_id: UUID = Depends(get_user_id), session: Session = Depends(get_session)
):
    try:
        push_notifications.unregister_token(session, user_id, device_id)
    except push_notifications.PushLocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Push device removed"}


@router.post(
    "/notifications/email", dependencies=[Depends(RequirePermission("notifications:send"))]
)
def email_notification(
    payload: EmailNotificationInput,
    request: Request,
    idempotency_key: IdempotencyKey,
    sender_id: UUID = Depends(get_user_id),
    session: Session = Depends(get_session),
):
    try:
        email_notifications.send_individual_email(
            session,
            request.app.state.settings,
            sender_id,
            payload.user_id,
            payload.subject,
            payload.message,
            idempotency_key,
        )
    except email_notifications.EmailRecipientNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmailUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"detail": "Email accepted for delivery"}


@router.get(
    "/notifications",
    response_model=list[NotificationRead],
    dependencies=[Depends(RequirePermission("notifications:read"))],
)
def list_notifications(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    return notifications.list_notifications(session, limit, offset)


@router.websocket("/notifications/live")
async def live_notifications(websocket: WebSocket):
    try:
        await notifications.stream_notifications(websocket)
    except notifications.NotificationAuthenticationRequired:
        await websocket.close(code=4401, reason="Authentication required")
    except WebSocketDisconnect:
        return
    except RedisError:
        await websocket.close(code=1013, reason="Live notification service unavailable")
