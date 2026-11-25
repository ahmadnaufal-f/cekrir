"""Loopback-only Tuya Cloud Project account-linking proof of concept."""

import hmac
import os
import re
import time
from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import httpx
import uvicorn
from dotenv import dotenv_values
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, StringConstraints
from starlette.middleware.trustedhost import TrustedHostMiddleware

ENV_FILE = Path(__file__).resolve().parents[2] / ".env.tuya-qr-poc"
DATA_CENTERS = {
    "cn": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "us-east": "https://openapi-ueaz.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "eu-west": "https://openapi-weaz.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
    "sg": "https://openapi-sg.iotbing.com",
}

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


class TuyaError(Exception):
    pass


class TuyaProject:
    def __init__(self, client: httpx.Client, access_id: str, access_secret: str):
        self.client = client
        self.access_id = access_id
        self.access_secret = access_secret

    def _request(self, method: str, path: str, access_token: str = "", *, operation: str) -> object:
        timestamp = str(time.time_ns() // 1_000_000)
        nonce = uuid4().hex
        # These Cloud Project requests have no body or custom signed headers.
        to_sign = f"{method}\n{sha256(b'').hexdigest()}\n\n{path}"
        message = f"{self.access_id}{access_token}{timestamp}{nonce}{to_sign}"
        signature = hmac.new(self.access_secret.encode(), message.encode(), sha256)
        headers = {
            "client_id": self.access_id,
            "t": timestamp,
            "nonce": nonce,
            "sign_method": "HMAC-SHA256",
            "sign": signature.hexdigest().upper(),
        }
        if access_token:
            headers["access_token"] = access_token

        try:
            response = self.client.request(method, path, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise TuyaError(f"Tuya returned HTTP {exc.response.status_code}.") from None
        except (httpx.RequestError, ValueError):
            raise TuyaError("Could not read a response from Tuya.") from None
        if not isinstance(data, dict):
            raise TuyaError("Tuya returned an unexpected response.")
        if data.get("success") is not True:
            code = str(data.get("code", ""))
            suffix = f" (code {code})" if code.isascii() and code.isdigit() else ""
            detail = f"Tuya returned an error during {operation}{suffix}."
            request_id = data.get("tid")
            if isinstance(request_id, str) and re.fullmatch(r"[0-9a-fA-F]{32}", request_id):
                detail += f" Tuya request ID {request_id}."
            raise TuyaError(detail)
        return data.get("result")

    def token(self) -> str:
        result = self._request(
            "GET", "/v1.0/token?grant_type=1", operation="project authentication"
        )
        token = result.get("access_token") if isinstance(result, dict) else None
        if not isinstance(token, str) or not token:
            raise TuyaError("Tuya returned no project access token.")
        return token

    def find_camera(self, link: CameraLink, access_token: str) -> CameraSummary | None:
        page_size = 50
        for page in range(1, 11):
            devices = self._request(
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
        result = self._request(
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
