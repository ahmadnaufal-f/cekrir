"""Loopback-only Tuya Cloud Project account-linking proof of concept."""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import httpx
import uvicorn
from dotenv import dotenv_values
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, StringConstraints
from starlette.middleware.trustedhost import TrustedHostMiddleware

from cekrir.services.tuya_cloud import DATA_CENTERS, TuyaCloud, TuyaError

ENV_FILE = Path(__file__).resolve().parents[2] / ".env.tuya-qr-poc"

TuyaId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$"
    ),
]


class CameraLink(BaseModel):
    uid: TuyaId
    device_id: TuyaId


class CameraSummary(BaseModel):
    name: str
    online: bool | None


class CaptureRequest(BaseModel):
    command_id: str


class TuyaProject(TuyaCloud):
    def token(self) -> str:
        result = self.request("GET", "/v1.0/token?grant_type=1", operation="project authentication")
        token = result.get("access_token") if isinstance(result, dict) else None
        if not isinstance(token, str) or not token:
            raise TuyaError("Tuya returned no project access token.")
        return token

    def find_camera(self, link: CameraLink, access_token: str) -> CameraSummary | None:
        page_size = 50
        for page in range(1, 11):
            devices = self.request(
                "GET",
                f"/v1.0/users/{link.uid}/devices?from=home&page_no={page}&page_size={page_size}",
                access_token,
                operation="linked account device lookup",
            )
            if not isinstance(devices, list):
                raise TuyaError("Tuya returned an unexpected device list.")
            for device in devices:
                if isinstance(device, dict) and device.get("id") == link.device_id:
                    name = device.get("name")
                    online = device.get("online")
                    return CameraSummary(
                        name=name if isinstance(name, str) and name else "Camera",
                        online=online if isinstance(online, bool) else None,
                    )
            if len(devices) < page_size:
                return None
        raise TuyaError("The camera was not found within the first 500 devices.")

    def request_capture(self, link: CameraLink, access_token: str) -> CaptureRequest:
        result = self.request(
            "POST",
            f"/v1.0/cameras/{link.device_id}/actions/capture",
            access_token,
            operation="snapshot capture",
        )
        command_id = result.get("sn") if isinstance(result, dict) else None
        if not isinstance(command_id, str) or not command_id:
            raise TuyaError("Tuya returned no capture command ID.")
        return CaptureRequest(command_id=command_id)


def project_client() -> Iterator[TuyaProject]:
    settings = dotenv_values(ENV_FILE, interpolate=False)
    access_id = os.getenv("TUYA_POC_ACCESS_ID") or settings.get("TUYA_POC_ACCESS_ID")
    access_secret = os.getenv("TUYA_POC_ACCESS_SECRET") or settings.get("TUYA_POC_ACCESS_SECRET")
    data_center = os.getenv("TUYA_POC_DATA_CENTER") or settings.get("TUYA_POC_DATA_CENTER")
    if not access_id or not access_secret or data_center not in DATA_CENTERS:
        raise HTTPException(503, "Configure the project credentials and data center for this POC.")
    with httpx.Client(base_url=DATA_CENTERS[data_center], timeout=10.0) as client:
        yield TuyaProject(client, access_id, access_secret)


app = FastAPI(title="Cekrir Tuya QR POC", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
Project = Annotated[TuyaProject, Depends(project_client)]


@app.middleware("http")
async def local_only(request: Request, call_next):
    if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
        return JSONResponse({"detail": "Open the POC on the local machine."}, status_code=403)
    if request.method == "POST" and request.headers.get("origin") != str(request.base_url).rstrip(
        "/"
    ):
        return JSONResponse({"detail": "Open this page before making a request."}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; img-src blob:; style-src 'unsafe-inline'; "
        "script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


@app.exception_handler(TuyaError)
async def cloud_error(_request: Request, error: TuyaError) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=502)


@app.get("/")
def page() -> FileResponse:
    return FileResponse(Path(__file__).with_name("tuya_qr_poc.html"), media_type="text/html")


def verify_camera(project: TuyaProject, link: CameraLink, token: str) -> CameraSummary:
    camera = project.find_camera(link, token)
    if camera is None:
        raise HTTPException(404, "This camera is not listed for the linked account.")
    return camera


@app.post("/api/verify")
def verify(link: CameraLink, project: Project) -> CameraSummary:
    return verify_camera(project, link, project.token())


@app.post("/api/capture")
def capture(link: CameraLink, project: Project) -> CaptureRequest:
    token = project.token()
    verify_camera(project, link, token)
    return project.request_capture(link, token)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003, proxy_headers=False, access_log=False)
