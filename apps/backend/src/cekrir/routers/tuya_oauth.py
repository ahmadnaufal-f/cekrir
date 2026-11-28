import logging
from secrets import token_urlsafe
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from cekrir.middleware import RequirePermission
from cekrir.middleware.role_permissions import TUYA_OAUTH_CALLBACK_PATH
from cekrir.services.tuya_cloud import DATA_CENTERS, TuyaCloud, TuyaError

router = APIRouter(tags=["tuya-oauth"])
STATE_PREFIX = "cekrir:tuya-oauth:sg:"
ANDROID_APPLICATION_ID = "id.cekrir.app"
TOKEN_PATH = "/v1.0/token"
PRIVATE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def _omit_oauth_queries(record: logging.LogRecord) -> bool:
    args = record.args
    if not isinstance(args, tuple):
        return True
    if record.name == "uvicorn.access" and len(args) == 5:
        return str(args[2]).partition("?")[0] != TUYA_OAUTH_CALLBACK_PATH
    if record.name == "httpx" and len(args) == 5:
        url = args[1]
        if isinstance(url, httpx.URL):
            return not (url.path == TOKEN_PATH and url.params.get("grant_type") == "2")
    return True


def protect_callback_logs() -> None:
    logging.getLogger("uvicorn.access").addFilter(_omit_oauth_queries)
    logging.getLogger("httpx").addFilter(_omit_oauth_queries)


def _reply(detail: str, status: int = 200) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status, headers=PRIVATE_HEADERS)


@router.post(
    "/api/v1/integrations/tuya/oauth/start/sg",
    dependencies=[Depends(RequirePermission("locations:manage"))],
)
def start(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    if not (
        settings.tuya_oauth_h5_url
        and settings.tuya_oauth_client_id
        and settings.tuya_oauth_client_secret
        and settings.tuya_oauth_android_sha1
    ):
        return _reply("Configure the Tuya app authorization and H5 page first.", 503)

    login_url = httpx.URL(str(settings.tuya_oauth_h5_url))
    redirect_urls = login_url.params.get_list("redirect_uri")
    if (
        login_url.scheme != "https"
        or login_url.userinfo
        or login_url.params.get_list("client_id") != [settings.tuya_oauth_client_id]
        or len(redirect_urls) != 1
        or not redirect_urls[0].startswith("https://")
        or httpx.URL(redirect_urls[0]).path != TUYA_OAUTH_CALLBACK_PATH
    ):
        return _reply("Save the Singapore callback and app key in the Tuya H5 configuration.", 503)

    state = token_urlsafe(32)
    try:
        saved = request.app.state.redis.client.set(
            f"{STATE_PREFIX}{state}", "pending", ex=600, nx=True
        )
    except RedisError:
        saved = False
    if not saved:
        return _reply("Could not start Tuya authorization. Try again.", 503)

    return JSONResponse(
        {"authorization_url": str(login_url.copy_set_param("state", state))},
        headers=PRIVATE_HEADERS,
    )


@router.get(TUYA_OAUTH_CALLBACK_PATH)
def callback(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    client_id = settings.tuya_oauth_client_id
    secret = settings.tuya_oauth_client_secret
    fingerprint = settings.tuya_oauth_android_sha1
    if not (client_id and secret and fingerprint):
        return _reply("Tuya app authorization is unavailable.", 503)

    states = request.query_params.getlist("state")
    codes = request.query_params.getlist("code")
    if len(states) != 1 or len(states[0]) != 43 or not states[0].isascii():
        return _reply("Start a new Tuya authorization from Cekrir.", 400)
    if len(codes) != 1 or not 0 < len(codes[0]) <= 1024 or "error" in request.query_params:
        return _reply("Tuya authorization did not provide a code.", 400)

    try:
        pending = request.app.state.redis.client.getdel(f"{STATE_PREFIX}{states[0]}")
    except RedisError:
        return _reply("Could not verify Tuya authorization. Try again.", 503)
    if pending != "pending":
        return _reply("Tuya authorization expired or was already used. Start again.", 400)

    query = urlencode({"code": codes[0], "grant_type": "2"})
    identifier = f"{fingerprint.upper()}{ANDROID_APPLICATION_ID}"
    try:
        with httpx.Client(base_url=DATA_CENTERS["sg"], timeout=10.0) as client:
            tuya = TuyaCloud(client, client_id, secret.get_secret_value(), identifier=identifier)
            result = tuya.request("GET", f"{TOKEN_PATH}?{query}", operation="OAuth code exchange")
    except TuyaError as error:
        return _reply(str(error), 502)

    access_token = result.get("access_token") if isinstance(result, dict) else None
    if not isinstance(access_token, str) or not access_token:
        return _reply("Tuya returned no OAuth access token.", 502)
    return _reply("Tuya authorization succeeded. You can close this page.")
