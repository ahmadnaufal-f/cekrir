"""BinderByte tracking requests; never expose its query-string API key."""

import http.client
import json
from urllib.parse import urlencode

from cekrir.config import Settings
from cekrir.validation.tracking import BinderByteInput


class BinderByteUnavailable(Exception):
    pass


def check_tracking(settings: Settings, payload: BinderByteInput) -> dict:
    if (
        not settings.binderbyte_api_key
        or not settings.binderbyte_api_key.get_secret_value().strip()
    ):
        raise BinderByteUnavailable("BinderByte is not configured")
    params = {
        "api_key": settings.binderbyte_api_key.get_secret_value(),
        "courier": payload.courier,
        "awb": payload.resi_number,
    }
    if payload.phone_last_five:
        params["number"] = payload.phone_last_five
    connection = http.client.HTTPSConnection("api.binderbyte.com", timeout=10)
    try:
        # The key is in BinderByte's required query string; avoid HTTP clients
        # that log full request URLs at INFO level and never follow redirects.
        connection.request("GET", f"/v1/track?{urlencode(params)}")
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Provider request failed")
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Provider response too large")
        body = json.loads(raw)
        if (
            not isinstance(body, dict)
            or body.get("status") != 200
            or not isinstance(body.get("data"), dict)
        ):
            raise ValueError("Invalid provider response")
        data = body["data"]
        if not isinstance(data.get("summary"), dict) or not isinstance(data.get("history"), list):
            raise ValueError("Invalid provider response")
        return {
            "summary": data["summary"],
            "detail": data.get("detail") or {},
            "history": data["history"],
        }
    except (http.client.HTTPException, OSError, ValueError, TypeError) as exc:
        raise BinderByteUnavailable("BinderByte tracking is unavailable") from exc
    finally:
        connection.close()
