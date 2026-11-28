import re
from secrets import compare_digest

import anyio
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.routing import Match

from cekrir.services.auth import authenticate_token

TUYA_OAUTH_CALLBACK_PATH = "/api/v1/integrations/tuya/oauth/callback/sg"


class RequirePermission:
    """Declare a permission on a route with Depends(RequirePermission(...))."""

    def __init__(self, permission: str, *, allow_ingest_key: bool = False):
        if not permission.strip():
            raise ValueError("A permission is required")
        self.permission = permission
        self.allow_ingest_key = allow_ingest_key

    def __call__(self, request: Request) -> None:
        if self.allow_ingest_key and getattr(request.state, "ingest_authenticated", False):
            return
        principal = getattr(request.state, "principal", None)
        if principal is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if self.permission not in principal["permissions"]:
            raise HTTPException(status_code=403, detail="Insufficient role")


class RolePermissionMiddleware(BaseHTTPMiddleware):
    """Authenticate API requests; each protected route declares its own permission."""

    PUBLIC_PATHS = {
        "/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self.PUBLIC_PATHS or not path.startswith("/api/v1/"):
            return await call_next(request)
        if request.method == "GET" and path == TUYA_OAUTH_CALLBACK_PATH:
            return await call_next(request)
        # This one route uses its own per-device credential dependency.
        if request.method == "POST" and re.fullmatch(
            r"/api/v1/devices/[A-Za-z0-9._:-]+/frames", path
        ):
            return await call_next(request)

        permissions = self._route_permissions(request)
        is_ingest = any(permission.allow_ingest_key for permission in permissions)
        if is_ingest and request.app.state.settings.ingest_api_key:
            if not self._has_valid_ingest_key(request):
                return JSONResponse(status_code=401, content={"detail": "Invalid ingestion key"})
            request.state.principal = None
            request.state.ingest_authenticated = True
            return await call_next(request)

        token = self._bearer_token(request)
        if token is None:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        principal = await anyio.to_thread.run_sync(
            authenticate_token,
            token,
            request.app.state.settings,
            request.app.state.session_factory,
        )
        if principal is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        request.state.principal = principal
        if not permissions:
            return JSONResponse(status_code=403, content={"detail": "Insufficient role"})
        return await call_next(request)

    @staticmethod
    def _bearer_token(request: Request) -> str | None:
        authorization = request.headers.get("authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if separator and scheme.lower() == "bearer" and token.strip():
            return token.strip()
        return None

    @staticmethod
    def _has_valid_ingest_key(request: Request) -> bool:
        expected = request.app.state.settings.ingest_api_key
        supplied = request.headers.get("x-ingest-key")
        return bool(
            expected
            and supplied
            and compare_digest(supplied.encode(), expected.get_secret_value().encode())
        )

    @staticmethod
    def _route_permissions(request: Request) -> list[RequirePermission]:
        def permissions(route):
            return [
                dependency.dependency
                for dependency in route.dependencies
                if isinstance(dependency.dependency, RequirePermission)
            ]

        def find(routes):
            for route in routes:
                if route.matches(request.scope)[0] != Match.FULL:
                    continue
                if isinstance(route, APIRoute):
                    return permissions(route)
                contexts = getattr(route, "effective_route_contexts", None)
                if contexts is not None:
                    for context in contexts():
                        if context.matches(request.scope)[0] == Match.FULL:
                            return permissions(context)
                    return []
                included = getattr(route, "original_router", None)
                if included is not None:
                    return find(included.routes)
            return []

        return find(request.app.routes)
