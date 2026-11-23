"""Decode an ESP32 image locally using the backend's barcode decoder."""

import argparse
import io
import json
import math
import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from PIL import Image, ImageFilter, ImageOps
from pydantic import ValidationError

# Use the same decoder and image limits as the backend API.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from cekrir.config import Settings
from cekrir.services.barcodes import (
    MAX_FRAME_BYTES,
    MAX_FRAME_DIMENSION,
    MAX_FRAME_PIXELS,
    InvalidCameraFrame,
    decode_frame,
)
from cekrir.services.binderbyte import BinderByteUnavailable, check_tracking
from cekrir.validation.tracking import BinderByteInput


def lookup_anteraja(resi_number: str) -> dict:
    """Look up a barcode using the same BinderByte integration as the backend."""
    key = 'sk_wpt4aoodf3re2anpqp5kkitlzfu5zrbwaz8gpedcetyrsdu1hspfnw7zcva6adjp'
    payload = BinderByteInput(resi_number=resi_number, courier="anteraja")
    settings = Settings(_env_file=None, binderbyte_api_key=key)
    return check_tracking(settings, payload)


def prepare_for_backend(image_bytes: bytes) -> bytes:
    """Resize and compress a JPEG locally to the backend's accepted limits."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.format != "JPEG":
            raise InvalidCameraFrame("Frame must be a JPEG image")
        width, height = image.size
        scale = min(
            1.0,
            MAX_FRAME_DIMENSION / max(width, height),
            math.sqrt(MAX_FRAME_PIXELS / (width * height)),
        )
        image = image.convert("RGB")
        if scale < 1:
            size = (max(1, int(width * scale)), max(1, int(height * scale)))
            image = image.resize(size, Image.Resampling.LANCZOS)
        for quality in (95, 85, 75, 60, 45):
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality)
            if output.tell() <= MAX_FRAME_BYTES:
                print(f"Prepared a local {image.width} x {image.height} JPEG for decoding.")
                return output.getvalue()
    raise InvalidCameraFrame("Could not compress the image within the backend's 512 KiB limit")


def enhance_and_decode(
    image_bytes: bytes, output_path: Path | None = None, mirror_output: bool = False
) -> list[str]:
    """Try local image adjustments; never send the image over the internet."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        gray = image.convert("L")
        adjusted = ImageOps.autocontrast(gray)
        sharpened = adjusted.filter(ImageFilter.UnsharpMask(radius=2, percent=250, threshold=3))
        mirrored = ImageOps.mirror(sharpened)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            (mirrored if mirror_output else sharpened).save(output_path, format="PNG")
            print(f"Saved enhanced image: {output_path}")
        for candidate in (adjusted, sharpened, mirrored):
            output = io.BytesIO()
            candidate.save(output, format="JPEG", quality=100)
            if output.tell() > 512 * 1024:
                output = io.BytesIO()
                candidate.save(output, format="JPEG", quality=85)
            try:
                results = decode_frame(output.getvalue())
            except InvalidCameraFrame:
                continue
            if results:
                return results
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Read barcodes from an ESP32 JPEG image")
    parser.add_argument(
        "image",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "src" / "barcode-test.jpg",
        help="JPEG image path (default: apps/esp32/src/barcode-test.jpg)",
    )
    parser.add_argument(
        "--enhance",
        action="store_true",
        help="Try local contrast, sharpening, and mirroring if the original fails",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save a contrast-adjusted and sharpened PNG (requires --enhance)",
    )
    parser.add_argument(
        "--mirror-output", action="store_true", help="Mirror the saved enhanced PNG"
    )
    parser.add_argument(
        "--decode-only", action="store_true", help="Skip the BinderByte tracking request"
    )
    args = parser.parse_args()
    if args.output and not args.enhance:
        parser.error("--output requires --enhance")
    if args.output and args.output.suffix.lower() != ".png":
        parser.error("--output must have a .png extension")
    if args.output and args.output.resolve() == args.image.resolve():
        parser.error("--output must be different from the input image")
    if args.mirror_output and not args.output:
        parser.error("--mirror-output requires --output")

    try:
        image = args.image.read_bytes()
        try:
            barcodes = decode_frame(image)
        except InvalidCameraFrame:
            if not args.enhance:
                raise
            print("Original image exceeds backend limits or is invalid; preparing a local copy.")
            image = prepare_for_backend(image)
            barcodes = decode_frame(image)
        if args.enhance and (not barcodes or args.output):
            print("Trying local image adjustments...")
            adjusted_barcodes = enhance_and_decode(image, args.output, args.mirror_output)
            if not barcodes:
                barcodes = adjusted_barcodes
            print(barcodes)
    except (OSError, InvalidCameraFrame) as exc:
        print(f"Could not read image: {exc}", file=sys.stderr)
        return 1

    if not barcodes:
        print("No barcode found. Try better lighting, focus, or camera distance.")
        return 1

    for barcode in barcodes:
        print(f"Barcode: {barcode}")
    if args.decode_only:
        return 0
    unique_barcodes = list(dict.fromkeys(barcodes))
    if len(unique_barcodes) != 1:
        print("More than one barcode was found. Capture only one label to check tracking.")
        return 1
    try:
        print("Checking AnterAja tracking with BinderByte...")
        tracking = lookup_anteraja(unique_barcodes[0])
    except BinderByteUnavailable as exc:
        print(f"Tracking failed: {exc}", file=sys.stderr)
        return 1
    except ValidationError:
        print("Tracking failed: invalid tracking number or configuration.", file=sys.stderr)
        return 1
    print(json.dumps(tracking, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
