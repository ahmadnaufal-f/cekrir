import asyncio

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from cekrir.config import Settings
from cekrir.db.repository import ShipmentRepository
from cekrir.db.session import get_session
from cekrir.schemas import NotificationRead
from cekrir.services.auth import authenticate_token

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    return ShipmentRepository(session).list_notifications(limit, offset)


@router.websocket("/notifications/live")
async def live_notifications(websocket: WebSocket):
    settings: Settings = websocket.app.state.settings
    authorization = websocket.headers.get("authorization", "")
    scheme, separator, header_token = authorization.partition(" ")
    token = header_token.strip() if separator and scheme.lower() == "bearer" else None
    token = token or websocket.query_params.get("token")

    principal = None
    if token:
        principal = await run_in_threadpool(
            authenticate_token,
            token,
            settings,
            websocket.app.state.session_factory,
        )
    if principal is None or "notifications:read" not in principal["permissions"]:
        await websocket.close(code=4401, reason="Authentication required")
        return

    await websocket.accept()
    try:
        async with websocket.app.state.redis.async_client.pubsub() as pubsub:
            await pubsub.subscribe("cekrir:notifications")
            await websocket.send_json({"type": "ready"})
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    await websocket.send_text(message["data"])
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                except TimeoutError:
                    pass
    except WebSocketDisconnect:
        return
    except RedisError:
        await websocket.close(code=1013, reason="Live notification service unavailable")
