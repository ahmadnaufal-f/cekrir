"""Standalone LAN camera receiver; it does not require PostgreSQL or Redis."""

from fastapi import FastAPI

from cekrir.routers.live_camera import router
from cekrir.services.live_camera import LatestFrame


def create_camera_app(username: str, password: str) -> FastAPI:
    if not username or len(password) < 12 or password == "CHANGE_ME":
        raise ValueError("Set a camera username and a password of at least 12 characters")
    app = FastAPI(title="Cekrir live camera", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.camera_user = username
    app.state.camera_password = password
    app.state.latest_frame = LatestFrame()
    app.include_router(router)
    return app
