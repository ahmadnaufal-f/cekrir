from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def camera_auth(request: Request, credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    expected_user = request.app.state.camera_user.encode()
    expected_password = request.app.state.camera_password.encode()
    if not (
        compare_digest(credentials.username.encode(), expected_user)
        and compare_digest(credentials.password.encode(), expected_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect camera username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
