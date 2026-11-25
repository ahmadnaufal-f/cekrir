import hmac
import re
import time
from hashlib import sha256
from uuid import uuid4

import httpx

DATA_CENTERS = {
    "cn": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "us-east": "https://openapi-ueaz.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "eu-west": "https://openapi-weaz.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
    "sg": "https://openapi-sg.iotbing.com",
}


class TuyaError(Exception):
    pass


class TuyaCloud:
    def __init__(
        self, client: httpx.Client, access_id: str, access_secret: str, *, identifier: str = ""
    ):
        self.client = client
        self.access_id = access_id
        self.access_secret = access_secret
        self.identifier = identifier

    def request(self, method: str, path: str, access_token: str = "", *, operation: str) -> object:
        timestamp = str(time.time_ns() // 1_000_000)
        nonce = uuid4().hex
        # These Cloud Project requests have no body or custom signed headers.
        to_sign = f"{method}\n{sha256(b'').hexdigest()}\n\n{path}"
        message = f"{self.access_id}{access_token}{timestamp}{nonce}{self.identifier}{to_sign}"
        signature = hmac.new(self.access_secret.encode(), message.encode(), sha256)
        headers = {
            "client_id": self.access_id,
            "t": timestamp,
            "nonce": nonce,
            "sign_method": "HMAC-SHA256",
            "sign": signature.hexdigest().upper(),
        }
        if access_token:
            headers["access_token"] = access_token

        try:
            response = self.client.request(method, path, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise TuyaError(f"Tuya returned HTTP {exc.response.status_code}.") from None
        except (httpx.RequestError, ValueError):
            raise TuyaError("Could not read a response from Tuya.") from None
        if not isinstance(data, dict):
            raise TuyaError("Tuya returned an unexpected response.")
        if data.get("success") is not True:
            code = str(data.get("code", ""))
            suffix = f" (code {code})" if code.isascii() and code.isdigit() else ""
            detail = f"Tuya returned an error during {operation}{suffix}."
            request_id = data.get("tid")
            if isinstance(request_id, str) and re.fullmatch(r"[0-9a-fA-F]{32}", request_id):
                detail += f" Tuya request ID {request_id}."
            raise TuyaError(detail)
        return data.get("result")
