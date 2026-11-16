from secrets import compare_digest

import anyio
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from cekrir.services.auth import authenticate_token


class RolePermissionMiddleware(BaseHTTPMiddleware):
    """Authenticate API requests and apply the current route role policy."""

    PUBLIC_PATHS = {
        "/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
    }
    ROUTE_PERMISSIONS = {
        ("GET", "/api/v1/shipments"): "shipments:read",
        ("POST", "/api/v1/shipments"): "shipments:create",
        ("GET", "/api/v1/notifications"): "notifications:read",
        ("POST", "/api/v1/detections"): "detections:create",
        ("POST", "/api/v1/detections/frame"): "detections:create",
        ("POST", "/api/v1/payments"): "payments:create",
        ("GET", "/api/v1/auth/users"): "users:read",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self.PUBLIC_PATHS or not path.startswith("/api/v1/"):
            return await call_next(request)

        is_ingest = request.method == "POST" and path in {
            "/api/v1/detections",
            "/api/v1/detections/frame",
        }
        if is_ingest and request.app.state.settings.ingest_api_key:
            if not self._has_valid_ingest_key(request):
                return JSONResponse(status_code=401, content={"detail": "Invalid ingestion key"})
            request.state.principal = None
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
        permission = self._permission_for(request.method, path)
        if permission is None or permission not in principal["permissions"]:
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

    @classmethod
    def _permission_for(cls, method: str, path: str) -> str | None:
        if method == "GET" and path.startswith("/api/v1/payments/"):
            return "payments:read"
        if method == "PATCH" and path.startswith("/api/v1/auth/users/") and path.endswith("/role"):
            return "users:role:update"
        if method == "POST" and path.startswith("/api/v1/shipments/") and path.endswith("/refresh"):
            return "shipments:refresh"
        return cls.ROUTE_PERMISSIONS.get((method, path))
