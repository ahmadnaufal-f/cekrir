from io import BytesIO
from unittest.mock import patch

import pytest
import zxingcpp
from PIL import Image
from pydantic import SecretStr

from cekrir.services.barcodes import MAX_FRAME_BYTES
from cekrir.services.binderbyte import BinderByteUnavailable

HEADERS = {"Content-Type": "image/jpeg", "X-Ingest-Key": "test-key"}
PARAMS = {"courier": "JNE", "camera_id": "esp32-front-door"}
ENDPOINT = "/api/v1/detections/frame"


def jpeg(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="JPEG", quality=95)
    return output.getvalue()


def barcode_image(text: str, barcode_format=zxingcpp.BarcodeFormat.Code128) -> Image.Image:
    barcode = zxingcpp.create_barcode(text, barcode_format)
    return Image.fromarray(zxingcpp.write_barcode_to_image(barcode, scale=3))


@pytest.mark.parametrize(
    "barcode_format,text",
    [
        (zxingcpp.BarcodeFormat.Code128, "CEKRIR128001"),
        (zxingcpp.BarcodeFormat.Code39, "CEKRIR39001"),
        (zxingcpp.BarcodeFormat.ITF, "123456789012"),
        (zxingcpp.BarcodeFormat.QRCode, "CEKRIRQR001"),
    ],
)
def test_camera_jpeg_to_shipment_and_notification(client, provider, barcode_format, text):
    frame = jpeg(barcode_image(text, barcode_format))
    response = client.post(ENDPOINT, params=PARAMS, content=frame, headers=HEADERS)
    assert response.status_code == 200
    result = response.json()
    assert result["detected_count"] == 1
    assert result["ambiguous"] is False
    assert result["detections"][0]["resi_number"] == text
    assert result["detections"][0]["created"] is True
    shipment = client.get("/api/v1/shipments").json()[0]
    assert shipment["camera_id"] == "esp32-front-door"
    assert shipment["courier"] == "jne"
    assert shipment["source"] == "camera"
    assert shipment["id"] == result["detections"][0]["shipment_id"]
    assert len(client.get("/api/v1/notifications").json()) == 1
    repeated = client.post(ENDPOINT, params=PARAMS, content=frame, headers=HEADERS)
    assert repeated.json()["detections"][0]["created"] is False
    assert len(client.get("/api/v1/notifications").json()) == 1
    assert provider.calls == 0


def test_blank_frame_and_unrelated_qr_do_not_create_shipments(client, provider):
    for image in [
        Image.new("L", (640, 480), color=255),
        barcode_image("https://example.com", zxingcpp.BarcodeFormat.QRCode),
    ]:
        result = client.post(ENDPOINT, params=PARAMS, content=jpeg(image), headers=HEADERS)
        assert result.status_code == 200
        assert result.json() == {"detected_count": 0, "ambiguous": False, "detections": []}
    assert provider.calls == 0
    assert client.get("/api/v1/shipments").json() == []


def test_multiple_resi_candidates_are_not_guessed(client, provider):
    first = barcode_image("CEKRIR001")
    second = barcode_image("CEKRIR002")
    frame = Image.new(
        "L", (max(first.width, second.width) + 40, first.height + second.height + 80), 255
    )
    frame.paste(first, (20, 20))
    frame.paste(second, (20, first.height + 60))
    response = client.post(ENDPOINT, params=PARAMS, content=jpeg(frame), headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"detected_count": 0, "ambiguous": True, "detections": []}
    assert provider.calls == 0


def test_frame_requires_the_ingestion_key(client):
    response = client.post(
        ENDPOINT, params=PARAMS, content=b"jpeg", headers={"Content-Type": "image/jpeg"}
    )
    assert response.status_code == 401


def test_frame_rejects_wrong_media_type_and_invalid_jpeg(client):
    response = client.post(
        ENDPOINT, params=PARAMS, content=b"jpeg", headers={**HEADERS, "Content-Type": "image/png"}
    )
    assert response.status_code == 415
    for content in [b"", b"not-a-jpeg"]:
        response = client.post(ENDPOINT, params=PARAMS, content=content, headers=HEADERS)
        assert response.status_code == 422
    png = BytesIO()
    Image.new("L", (100, 100), 255).save(png, format="PNG")
    assert (
        client.post(ENDPOINT, params=PARAMS, content=png.getvalue(), headers=HEADERS).status_code
        == 422
    )


def test_large_body_and_large_dimensions_are_rejected(client):
    response = client.post(
        ENDPOINT, params=PARAMS, content=b"x" * (MAX_FRAME_BYTES + 1), headers=HEADERS
    )
    assert response.status_code == 413
    response = client.post(
        ENDPOINT, params=PARAMS, content=jpeg(Image.new("L", (2049, 1536), 255)), headers=HEADERS
    )
    assert response.status_code == 422


def test_chunked_upload_cannot_bypass_the_body_limit(client):
    chunks = (b"x" * (64 * 1024) for _ in range(9))
    response = client.post(ENDPOINT, params=PARAMS, content=chunks, headers=HEADERS)
    assert response.status_code == 413


def test_camera_arrival_does_not_depend_on_tracking_provider(client, provider):
    provider.fail = True
    response = client.post(
        ENDPOINT, params=PARAMS, content=jpeg(barcode_image("CEKRIR001")), headers=HEADERS
    )
    assert response.status_code == 200
    assert client.get("/api/v1/shipments").json()[0]["status"] == "delivered"
    assert len(client.get("/api/v1/notifications").json()) == 1
    assert provider.calls == 0


def test_camera_metadata_is_validated(client):
    for params in [{"courier": "jne"}, {"courier": "j&bad", "camera_id": "door"}]:
        response = client.post(ENDPOINT, params=params, content=b"jpeg", headers=HEADERS)
        assert response.status_code == 422


def test_missing_courier_returns_barcode_without_creating_shipment(client):
    frame = jpeg(barcode_image("CEKRIR001"))
    for params in ({"camera_id": "door"}, {"camera_id": "door", "courier": ""}):
        response = client.post(ENDPOINT, params=params, content=frame, headers=HEADERS)
        assert response.status_code == 200
        detection = response.json()["detections"][0]
        assert detection["resi_number"] == "CEKRIR001"
        assert detection["shipment_id"] is None
        assert detection["tracking"] is None
    assert client.get("/api/v1/shipments").json() == []


def test_first_detection_looks_up_configured_courier_once(client):
    client.app.state.settings.binderbyte_api_key = SecretStr("test-key")
    client.app.state.settings.binderbyte_detection_courier = "anteraja"
    payload = {"resi_number": "CEKRIR123", "courier": "anteraja"}
    assert client.post("/api/v1/shipments", json=payload).status_code == 201
    frame = jpeg(barcode_image("CEKRIR123"))
    params = {"camera_id": "door", "courier": "anteraja"}
    tracking = {"summary": {"status": "ON PROCESS"}, "detail": {}, "history": []}
    with patch("cekrir.services.detections.check_tracking", return_value=tracking) as lookup:
        first = client.post(ENDPOINT, params=params, content=frame, headers=HEADERS)
        second = client.post(ENDPOINT, params=params, content=frame, headers=HEADERS)
    assert first.status_code == second.status_code == 200
    assert first.json()["detections"][0]["tracking"] == tracking
    assert second.json()["detections"][0]["tracking"] is None
    assert lookup.call_count == 1
    assert lookup.call_args.args[1].courier == "anteraja"


def test_blank_or_different_courier_does_not_call_binderbyte(client):
    client.app.state.settings.binderbyte_api_key = SecretStr("test-key")
    frame = jpeg(barcode_image("CEKRIR123"))
    with patch("cekrir.services.detections.check_tracking") as lookup:
        result = client.post(ENDPOINT, params=PARAMS, content=frame, headers=HEADERS)
        client.app.state.settings.binderbyte_detection_courier = "anteraja"
        result2 = client.post(
            ENDPOINT, params=PARAMS, content=jpeg(barcode_image("CEKRIR456")), headers=HEADERS
        )
    assert result.status_code == result2.status_code == 200
    assert result.json()["detections"][0]["tracking"] is None
    assert result2.json()["detections"][0]["tracking"] is None
    lookup.assert_not_called()


def test_tracking_failure_does_not_lose_detection(client):
    client.app.state.settings.binderbyte_api_key = SecretStr("test-key")
    client.app.state.settings.binderbyte_detection_courier = "anteraja"
    with patch(
        "cekrir.services.detections.check_tracking", side_effect=BinderByteUnavailable("offline")
    ):
        response = client.post(
            ENDPOINT,
            params={"camera_id": "door", "courier": "anteraja"},
            content=jpeg(barcode_image("CEKRIR123")),
            headers=HEADERS,
        )
    assert response.status_code == 200
    assert response.json()["detections"][0]["shipment_id"] is not None
    assert response.json()["detections"][0]["tracking"] is None


def test_three_megapixel_frame_is_resized_and_decoded(client):
    frame = Image.new("L", (2048, 1536), 255)
    frame.paste(barcode_image("CEKRIR123"), (600, 650))
    response = client.post(ENDPOINT, params=PARAMS, content=jpeg(frame), headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["detections"][0]["resi_number"] == "CEKRIR123"
