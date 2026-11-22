"""Export OpenAPI specs for both applications without starting their servers."""

import json
from pathlib import Path

from cekrir.live_camera_app import create_camera_app
from cekrir.main import create_app

OUTPUT = Path(__file__).resolve().parents[1] / "api"
PUBLIC_PATHS = {
    "/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/resend-verification",
}


def main() -> None:
    main_spec = create_app().openapi()
    main_spec["info"]["description"] = (
        "Main Cekrir API. See API.md for middleware permissions, conditional ingestion "
        "authentication, and the WebSocket and verification page."
    )
    schemes = main_spec.setdefault("components", {}).setdefault("securitySchemes", {})
    schemes["BearerAuth"] = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    schemes["IngestKey"] = {"type": "apiKey", "in": "header", "name": "X-Ingest-Key"}
    schemes["DeviceKey"] = {"type": "apiKey", "in": "header", "name": "X-Device-Key"}
    for path, methods in main_spec["paths"].items():
        if path in PUBLIC_PATHS:
            continue
        for method, operation in methods.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            operation["security"] = [{"BearerAuth": []}]
            if method == "post" and path == "/api/v1/devices/{device_id}/frames":
                operation["security"] = [{"DeviceKey": []}]
            if method == "post" and path in {"/api/v1/detections", "/api/v1/detections/frame"}:
                operation["security"].append({"IngestKey": []})
                operation["description"] = (
                    "When CEKRIR_INGEST_API_KEY is configured, the matching X-Ingest-Key "
                    "is required; otherwise use a bearer token with detections:create."
                )

    camera_spec = create_camera_app("camera", "example-password").openapi()
    camera_spec["info"]["description"] = (
        "Standalone LAN camera server, separate from the main API; see API.md."
    )
    camera_spec["paths"]["/camera/frame"]["post"]["requestBody"] = {
        "required": True,
        "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
    }
    camera_spec["paths"]["/camera/latest.jpg"]["get"]["responses"]["200"]["content"] = {
        "image/jpeg": {"schema": {"type": "string", "format": "binary"}}
    }
    camera_spec["paths"]["/camera/stream"]["get"]["responses"]["200"]["content"] = {
        "multipart/x-mixed-replace": {
            "schema": {"type": "string", "format": "binary"},
            "description": "Continuous multipart MJPEG; boundary is frame.",
        }
    }
    OUTPUT.mkdir(exist_ok=True)
    for filename, spec in (("openapi.json", main_spec), ("camera-openapi.json", camera_spec)):
        (OUTPUT / filename).write_text(
            json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
