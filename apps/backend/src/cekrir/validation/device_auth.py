from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from cekrir.db.session import get_session
from cekrir.services import devices


def verified_esp(
    device_id: str,
    session: Annotated[Session, Depends(get_session)],
    device_key: Annotated[str | None, Header(alias="X-Device-Key", max_length=128)] = None,
) -> tuple[str, UUID]:
    try:
        return devices.authenticate_esp(session, device_id, device_key)
    except devices.DeviceAuthenticationFailed as exc:
        raise HTTPException(status_code=401, detail="Invalid device credentials") from exc
