"""PC-side tool: save JPEGs from the camera-check firmware over USB."""

import argparse
import time
from pathlib import Path

import serial

MAX_JPEG_BYTES = 2_000_000
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "captures" / "camera-check.jpg"


def capture(port: serial.Serial) -> bytes:
    print("Asking the ESP32 for a picture; waiting up to 30 seconds...", flush=True)
    port.write(b"c")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        line = port.readline()
        if not line:
            continue
        if not line.startswith(b"CEKRIR_JPEG "):
            print(line.decode("utf-8", errors="replace").strip())
            continue
        try:
            size = int(line.split()[1])
        except (ValueError, IndexError) as exc:
            raise RuntimeError("Invalid JPEG header from device") from exc
        if size <= 0 or size > MAX_JPEG_BYTES:
            raise RuntimeError("Invalid JPEG size from device")
        print(f"Receiving picture ({size} bytes)...", flush=True)
        # Serial transfers use roughly 10 bits per byte at 115200 baud.
        deadline = time.monotonic() + max(30, size * 20 / 115200 + 10)
        image = bytearray()
        while len(image) < size and time.monotonic() < deadline:
            image.extend(port.read(size - len(image)))
        if (
            len(image) != size
            or not image.startswith(b"\xff\xd8")
            or not image.endswith(b"\xff\xd9")
        ):
            raise RuntimeError("Incomplete or invalid JPEG received")
        return bytes(image)
    raise TimeoutError("No diagnostic JPEG received; check firmware, port, and camera")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Save camera-check JPEGs from an ESP32"
    )
    parser.add_argument("--port", required=True, help="Serial port, for example COM10")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--count", type=int, default=1, help="Number of images to capture"
    )
    parser.add_argument(
        "--interval", type=float, default=3, help="Seconds between captures"
    )
    args = parser.parse_args()
    if args.count < 1 or args.interval < 0:
        parser.error("count must be positive and interval cannot be negative")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        print(f"Connecting to {args.port}...", flush=True)
        with serial.Serial(args.port, 115200, timeout=1, write_timeout=5) as port:
            # Opening some serial adapters resets the board. Wait for initialization.
            print("Connected. Waiting 3 seconds for the board to start...", flush=True)
            time.sleep(3)
            for index in range(args.count):
                image = capture(port)
                args.output.write_bytes(image)
                print(
                    f"Saved {len(image)} bytes to {args.output} ({index + 1}/{args.count})"
                )
                if index + 1 < args.count:
                    time.sleep(args.interval)
    except (serial.SerialException, OSError, RuntimeError, TimeoutError) as exc:
        parser.exit(1, f"Camera capture failed: {exc}\n")


if __name__ == "__main__":
    main()
