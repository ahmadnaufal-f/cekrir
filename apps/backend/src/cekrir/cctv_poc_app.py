"""Local-only CCTV snapshot POC; intentionally independent of the main API/database."""

import os
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from cekrir.cctv_capture import CaptureError, capture_jpeg

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

app = FastAPI(title="Cekrir CCTV snapshot POC", docs_url=None, redoc_url=None)


@app.post("/snapshot", response_class=Response)
async def snapshot() -> Response:
    file_settings = dotenv_values(ENV_FILE)

    def setting(name: str) -> str:
        return os.getenv(name) or file_settings.get(name) or ""

    try:
        jpeg = await run_in_threadpool(
            capture_jpeg,
            setting("CEKRIR_CCTV_RTSP_URL"),
            setting("CEKRIR_CCTV_USERNAME"),
            setting("CEKRIR_CCTV_PASSWORD"),
        )
    except CaptureError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
