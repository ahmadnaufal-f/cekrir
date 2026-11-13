"""Optional edge worker. Install with `uv sync --extra vision` before running."""

import argparse
import logging
import os
import time

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from cekrir.schemas import DetectionInput

logger = logging.getLogger("cekrir.scanner")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Decode resi barcodes from a CCTV stream or webcam"
    )
    parser.add_argument(
        "--courier", required=True, help="Courier code, e.g. jne; not in most barcodes"
    )
    parser.add_argument("--camera-id", default="front-door")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between frame scans")
    parser.add_argument(
        "--cooldown", type=float, default=60.0, help="Seconds between duplicate posts"
    )
    args = parser.parse_args()
    if args.interval <= 0 or args.cooldown <= 0:
        parser.error("interval and cooldown must be positive")
    # Validate configuration before opening the camera.
    try:
        DetectionInput(resi_number="CHECK", courier=args.courier, camera_id=args.camera_id)
    except ValidationError:
        parser.error("Invalid courier code or camera ID")

    try:
        import cv2
        import zxingcpp
    except ImportError:
        parser.exit(1, "Install the vision extra first: uv sync --extra vision\n")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    source = os.getenv("CEKRIR_CAMERA_SOURCE", "0")
    capture = cv2.VideoCapture(int(source) if source.isdecimal() else source)
    # Do not log source: RTSP URLs often contain credentials.
    if not capture.isOpened():
        capture.release()
        parser.exit(1, "Could not open camera. Check CEKRIR_CAMERA_SOURCE and network access.\n")
    api_url = os.getenv("CEKRIR_API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
    key = os.getenv("CEKRIR_INGEST_API_KEY")
    headers = {"X-Ingest-Key": key} if key else {}
    seen: dict[str, float] = {}
    next_scan = 0.0
    try:
        with httpx.Client(timeout=10, headers=headers) as client:
            while True:
                # Drain frames continuously to avoid a growing RTSP buffer.
                ok, frame = capture.read()
                if not ok:
                    logger.error("Camera stream ended; restart the worker to reconnect")
                    break
                now = time.monotonic()
                if now < next_scan:
                    time.sleep(min(0.02, args.interval))
                    continue
                next_scan = now + args.interval
                seen = {code: last for code, last in seen.items() if now - last < args.cooldown}
                for barcode in zxingcpp.read_barcodes(frame):
                    try:
                        payload = DetectionInput(
                            resi_number=barcode.text, courier=args.courier, camera_id=args.camera_id
                        )
                    except ValidationError:
                        continue  # Ignore unrelated URLs and unrecognized label formats.
                    if payload.resi_number in seen:
                        continue
                    try:
                        response = client.post(f"{api_url}/detections", json=payload.model_dump())
                        response.raise_for_status()
                    except httpx.HTTPError:
                        # Suppress raw exception text: URLs may hold credentials.
                        logger.warning("Detection submission failed; retrying on a later frame")
                        continue
                    seen[payload.resi_number] = now
                    logger.info("Detection accepted for camera %s", args.camera_id)
    except KeyboardInterrupt:
        logger.info("Stopping scanner")
    finally:
        capture.release()


if __name__ == "__main__":
    main()
