"""Run the LAN camera receiver using the ESP32's local camera credentials."""

import re
from pathlib import Path

import uvicorn

from cekrir.live_camera_app import create_camera_app

config = Path(__file__).resolve().parents[1] / "esp32/include/wifi_camera_config.h"


def setting(name: str) -> str:
    content = config.read_text(encoding="utf-8")
    match = re.search(rf'constexpr\s+char\s+{name}\[\]\s*=\s*"([^"\\]*)"\s*;', content)
    if not match:
        raise ValueError(f"Could not read {name} from {config}")
    return match.group(1)


if __name__ == "__main__":
    try:
        app = create_camera_app(setting("kCameraUser"), setting("kCameraPassword"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Camera configuration error: {exc}") from exc
    print("Open http://localhost:8001/camera in your browser", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8001, access_log=False)
