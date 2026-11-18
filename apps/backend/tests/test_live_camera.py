import asyncio
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from cekrir.live_camera_app import create_camera_app
from cekrir.services.live_camera import LatestFrame


def test_live_camera_receives_and_serves_latest_image():
    client = TestClient(create_camera_app("camera", "a-long-password"))
    auth = ("camera", "a-long-password")
    assert client.get("/camera").status_code == 401
    assert client.get("/camera/video").status_code == 401
    assert client.get("/camera/stream").status_code == 401
    assert client.get("/camera", auth=("camera", "wrong")).status_code == 401
    assert client.get("/camera", auth=auth).status_code == 200
    assert client.get("/camera/video", auth=auth).status_code == 200
    assert client.get("/camera/latest.jpg", auth=auth).status_code == 404

    image = BytesIO()
    Image.new("RGB", (10, 10), "red").save(image, format="JPEG")
    frame = image.getvalue()
    headers = {"Content-Type": "image/jpeg"}
    assert client.post("/camera/frame", content=frame, headers=headers).status_code == 401
    invalid = client.post("/camera/frame", content=b"invalid", headers=headers, auth=auth)
    assert invalid.status_code == 422
    assert client.post("/camera/frame", content=frame, auth=auth).status_code == 415
    uploaded = client.post("/camera/frame", content=frame, headers=headers, auth=auth)
    assert uploaded.status_code == 200
    response = client.get("/camera/latest.jpg", auth=auth)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == frame
    oversized = client.post(
        "/camera/frame", content=b"x" * (512 * 1024 + 1), headers=headers, auth=auth
    )
    assert oversized.status_code == 413
    assert client.get("/camera/latest.jpg", auth=auth).content == frame


def test_stream_emits_new_frames_as_multipart_jpegs():
    def make_jpeg(color):
        data = BytesIO()
        Image.new("RGB", (10, 10), color).save(data, format="JPEG")
        return data.getvalue()

    async def check():
        store = LatestFrame()
        first, second = make_jpeg("red"), make_jpeg("blue")
        store.save(first)
        stream = store.stream()
        part = await asyncio.wait_for(anext(stream), timeout=1)
        assert part.startswith(b"--frame\r\nContent-Type: image/jpeg\r\n")
        assert first in part
        store.save(second)
        part = await asyncio.wait_for(anext(stream), timeout=1)
        assert second in part
        await stream.aclose()

    asyncio.run(check())
