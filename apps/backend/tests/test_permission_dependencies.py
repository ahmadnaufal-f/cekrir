from unittest.mock import patch

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from cekrir.config import Settings
from cekrir.middleware import RequirePermission, RolePermissionMiddleware


def make_client(*, ingest_key=None):
    app = FastAPI()
    app.state.settings = Settings(_env_file=None, ingest_api_key=ingest_key)
    app.state.session_factory = object()
    app.add_middleware(RolePermissionMiddleware)

    @app.post("/api/v1/items", dependencies=[Depends(RequirePermission("items:create"))])
    def create_item():
        return {"ok": True}

    @app.post(
        "/api/v1/ingest",
        dependencies=[Depends(RequirePermission("items:create", allow_ingest_key=True))],
    )
    def ingest():
        return {"ok": True}

    @app.get("/api/v1/unconfigured")
    def unconfigured():
        return {"ok": True}

    return TestClient(app)


def test_route_permission_requires_authentication_and_granted_permission():
    client = make_client()
    assert client.post("/api/v1/items").status_code == 401
    with patch("cekrir.middleware.role_permissions.authenticate_token") as authenticate:
        headers = {"Authorization": "Bearer test-token"}
        authenticate.return_value = None
        assert client.post("/api/v1/items", headers=headers).status_code == 401
        authenticate.return_value = {"permissions": set()}
        assert client.post("/api/v1/items", headers=headers).status_code == 403
        authenticate.return_value = {"permissions": {"items:create"}}
        assert client.post("/api/v1/items", headers=headers).status_code == 200
        assert client.get("/api/v1/unconfigured", headers=headers).status_code == 403


def test_ingest_key_only_grants_access_to_routes_that_allow_it():
    client = make_client(ingest_key="camera-key")
    assert client.post("/api/v1/ingest").status_code == 401
    assert client.post("/api/v1/ingest", headers={"X-Ingest-Key": "wrong"}).status_code == 401
    assert client.post("/api/v1/ingest", headers={"X-Ingest-Key": "camera-key"}).status_code == 200
    assert client.post("/api/v1/items", headers={"X-Ingest-Key": "camera-key"}).status_code == 401


def test_permission_dependency_fails_closed_without_middleware():
    app = FastAPI()

    @app.get("/items", dependencies=[Depends(RequirePermission("items:read"))])
    def items():
        return []

    assert TestClient(app).get("/items").status_code == 401


def test_permission_dependency_on_included_router_with_prefix():
    app = FastAPI()
    app.state.settings = Settings(_env_file=None)
    app.state.session_factory = object()
    app.add_middleware(RolePermissionMiddleware)
    router = APIRouter()

    @router.get("/items/{item_id}", dependencies=[Depends(RequirePermission("items:read"))])
    def read_item(item_id: int):
        return {"id": item_id}

    app.include_router(router, prefix="/api/v1")
    with patch("cekrir.middleware.role_permissions.authenticate_token") as authenticate:
        authenticate.return_value = {"permissions": {"items:read"}}
        response = TestClient(app).get(
            "/api/v1/items/123", headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 200
    assert response.json() == {"id": 123}
