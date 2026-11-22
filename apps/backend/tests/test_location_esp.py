from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from cekrir.db.model import EspDevice, Role, User
from cekrir.db.session import build_engine, get_session
from cekrir.dependencies import get_user_id
from cekrir.middleware import RequirePermission
from cekrir.routers.locations import router
from cekrir.services.location_management import (
    EspAlreadyAssigned,
    add_camera,
    assign_esp,
    create_location,
    list_owned_locations,
    remove_esp,
)
from cekrir.validation.locations import LocationCreate


def location_client():
    app = FastAPI()
    app.include_router(router)
    for route in router.routes:
        for dependency in getattr(route, "dependencies", []):
            if isinstance(dependency.dependency, RequirePermission):
                app.dependency_overrides[dependency.dependency] = lambda: None
    app.dependency_overrides[get_session] = lambda: object()
    app.dependency_overrides[get_user_id] = lambda: uuid4()
    return TestClient(app)


def test_location_and_esp_validation_before_service():
    client = location_client()
    with patch("cekrir.services.location_management.create_location") as create:
        assert client.post("/api/v1/locations", json={"name": "   "}).status_code == 422
        create.assert_not_called()
    with patch("cekrir.services.location_management.assign_esp") as assign:
        response = client.put(f"/api/v1/locations/{uuid4()}/esp/invalid%20id")
        assert response.status_code == 422
        assign.assert_not_called()


def test_esp_conflict_returns_409():
    client = location_client()
    with patch("cekrir.services.location_management.assign_esp", side_effect=EspAlreadyAssigned):
        assert client.put(f"/api/v1/locations/{uuid4()}/esp/device-1").status_code == 409


def test_esp_is_unique_and_assignment_is_idempotent():
    assert EspDevice.__table__.c.location_id.unique
    location_id, admin_id = uuid4(), uuid4()
    session = Mock()
    session.get.return_value = EspDevice(device_id="device-1", location_id=location_id)
    with patch("cekrir.services.location_management._owned_location"):
        assign_esp(session, location_id, admin_id, "device-1")
        session.commit.assert_called_once()
        session.get.return_value = EspDevice(device_id="device-1", location_id=uuid4())
        with pytest.raises(EspAlreadyAssigned):
            assign_esp(session, location_id, admin_id, "device-1")
        session.rollback.assert_called_once()


def test_location_onboarding_with_postgresql(database_url):
    engine = build_engine(database_url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                    admin = session.scalar(select(User).join(Role).where(Role.code == "admin"))
                    assert admin is not None
                    suffix = uuid4().hex
                    first = create_location(session, admin.id, LocationCreate(name="First"))
                    second = create_location(session, admin.id, LocationCreate(name="Second"))
                    assert first["onboarding_complete"] is False
                    device_id = f"esp-{suffix}"
                    assign_esp(session, first["id"], admin.id, device_id)
                    assign_esp(session, first["id"], admin.id, device_id)
                    with pytest.raises(EspAlreadyAssigned):
                        assign_esp(session, first["id"], admin.id, f"esp2-{suffix}")
                    with pytest.raises(EspAlreadyAssigned):
                        assign_esp(session, second["id"], admin.id, device_id)
                    add_camera(session, first["id"], admin.id, f"cam1-{suffix}")
                    add_camera(session, first["id"], admin.id, f"cam2-{suffix}")
                    location = next(
                        row
                        for row in list_owned_locations(session, admin.id)
                        if row["id"] == first["id"]
                    )
                    assert location["onboarding_complete"] is False  # awaiting a device check-in
                    assert location["esp_device_id"] == device_id
                    assert len(location["camera_ids"]) == 2
                    remove_esp(session, first["id"], admin.id)
                    location = next(
                        row
                        for row in list_owned_locations(session, admin.id)
                        if row["id"] == first["id"]
                    )
                    assert location["onboarding_complete"] is False
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
