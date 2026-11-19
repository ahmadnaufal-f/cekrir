from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.schemas import NotificationRead
from cekrir.services import notifications

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationRead])
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
