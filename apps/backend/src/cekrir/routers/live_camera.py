from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from cekrir.services.live_camera import InvalidLiveFrame
from cekrir.validation.camera import jpeg_frame
from cekrir.validation.live_camera import camera_auth

router = APIRouter(prefix="/camera", dependencies=[Depends(camera_auth)])


@router.post("/frame")
async def receive_frame(request: Request, frame: Annotated[bytes, Depends(jpeg_frame)]):
    try:
        await run_in_threadpool(request.app.state.latest_frame.save, frame)
    except InvalidLiveFrame as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "received"}


@router.get("/latest.jpg")
def latest_frame(request: Request):
    frame = request.app.state.latest_frame.get()
    if frame is None:
        raise HTTPException(status_code=404, detail="Waiting for the first picture")
    return Response(frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/stream")
def video_stream(request: Request):
    return StreamingResponse(
        request.app.state.latest_frame.stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/video", response_class=HTMLResponse)
def video_page():
    return HTMLResponse(
        "<!doctype html><meta name='viewport' content='width=device-width'>"
        "<title>ESP32 live video</title><h1>ESP32 live video</h1>"
        "<p>Waiting for the camera if no picture appears.</p>"
        "<img src='/camera/stream' alt='Waiting for video' style='max-width:100%'>",
        headers={"Cache-Control": "no-store"},
    )


@router.get("", response_class=HTMLResponse)
def camera_page():
    return HTMLResponse(
        "<!doctype html><meta name='viewport' content='width=device-width'>"
        "<title>ESP32 camera</title><h1>ESP32 camera</h1>"
        "<p>Showing the latest picture, refreshed every second.</p>"
        "<img id='picture' alt='Waiting for a picture' style='max-width:100%'>"
        "<script>const image=document.getElementById('picture');"
        "function refresh(){image.src='/camera/latest.jpg?t='+Date.now()}"
        "refresh();setInterval(refresh,1000);</script>",
        headers={"Cache-Control": "no-store"},
    )
