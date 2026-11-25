from io import BytesIO
from math import sqrt

import zxingcpp
from PIL import Image, UnidentifiedImageError

MAX_FRAME_BYTES = 512 * 1024
MAX_FRAME_PIXELS = 2_000_000
MAX_FRAME_DIMENSION = 2048
MAX_SOURCE_PIXELS = 4_000_000
BARCODE_FORMATS = (
    zxingcpp.BarcodeFormat.Code128,
    zxingcpp.BarcodeFormat.Code39,
    zxingcpp.BarcodeFormat.ITF,
    zxingcpp.BarcodeFormat.QRCode,
)


class InvalidCameraFrame(ValueError):
    pass


def decode_frame(jpeg: bytes) -> list[str]:
    """Decode a bounded JPEG in memory; footage is never persisted."""
    if not jpeg or len(jpeg) > MAX_FRAME_BYTES:
        raise InvalidCameraFrame("JPEG frame must contain 1 to 524288 bytes")
    try:
        with Image.open(BytesIO(jpeg)) as image:
            if image.format != "JPEG":
                raise InvalidCameraFrame("Frame must be a JPEG image")
            width, height = image.size
            # Check headers before decompressing an untrusted image.
            if max(width, height) > MAX_FRAME_DIMENSION or width * height > MAX_SOURCE_PIXELS:
                raise InvalidCameraFrame(
                    "Frame must be at most 4 megapixels and 2048 pixels per side"
                )
            image.load()
            image = image.convert("L")
            if width * height > MAX_FRAME_PIXELS:
                scale = sqrt(MAX_FRAME_PIXELS / (width * height))
                image = image.resize(
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    Image.Resampling.LANCZOS,
                )
            return [
                barcode.text
                for barcode in zxingcpp.read_barcodes(image, formats=BARCODE_FORMATS)
                if barcode.valid
            ]
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise InvalidCameraFrame("Frame is not a valid JPEG image") from exc
