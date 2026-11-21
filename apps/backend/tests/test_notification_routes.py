from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from cekrir.config import Settings
from cekrir.db.session import get_session
from cekrir.main import create_app


def test_location_and_individual_email_routes_check_permissions_and_validation():
    app = create_app(settings=Settings(_env_file=None))
    app.dependency_overrides[get_session] = lambda: object()
    user_id, location_id = uuid4(), uuid4()
    admin = {"id": str(user_id), "permissions": {"locations:manage", "notifications:send"}}
    member = {"id": str(uuid4()), "permissions": set()}
    with (
        patch("cekrir.middleware.role_permissions.authenticate_token") as authenticate,
        patch("cekrir.services.location_management.add_member") as assign,
        patch("cekrir.services.email_notifications.send_individual_email") as send,
    ):
        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        authenticate.return_value = member
        path = f"/api/v1/locations/{location_id}/members/{user_id}"
        assert client.put(path, headers=headers).status_code == 403
        assign.assert_not_called()
        authenticate.return_value = admin
        assert client.put(path, headers=headers).status_code == 200
        assign.assert_called_once()
        payload = {"user_id": str(user_id), "subject": "Hello", "message": "A message"}
        assert (
            client.post("/api/v1/notifications/email", headers=headers, json=payload).status_code
            == 422
        )
        response = client.post(
            "/api/v1/notifications/email",
            headers={**headers, "Idempotency-Key": "test-1"},
            json=payload,
        )
        assert response.status_code == 200
        send.assert_called_once()
        authenticate.return_value = member
        assert (
            client.post(
                "/api/v1/notifications/email",
                headers={**headers, "Idempotency-Key": "test-2"},
                json=payload,
            ).status_code
            == 403
        )
