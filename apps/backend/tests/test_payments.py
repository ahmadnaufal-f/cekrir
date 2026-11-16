from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete

from cekrir.config import Settings
from cekrir.db.model import Payment, User
from cekrir.db.session import build_engine, build_session_factory, get_session
from cekrir.middleware import RolePermissionMiddleware
from cekrir.routers.payments import PaymentCreate, router
from cekrir.services.auth import issue_token
from cekrir.services.payments import (
    IdempotencyConflict,
    PaymentDetails,
    create_payment,
    get_payment,
)


@pytest.mark.parametrize("amount", [0, -1, 10_000_001, 1.5, True, "100"])
def test_payment_amount_requires_valid_whole_rupiah(amount):
    with pytest.raises(ValidationError):
        PaymentCreate(reference="order-1", amount=amount)


def test_payment_routes_require_auth_and_idempotency_key():
    settings = Settings(_env_file=None, jwt_secret_key="a" * 48)
    user = SimpleNamespace(
        id=uuid4(),
        email="person@example.com",
        full_name="Person",
        role="member",
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, model, user_id):
            return user if user_id == user.id else None

        def scalars(self, statement):
            return ["payments:create", "payments:read"]

    app = FastAPI()
    app.state.settings = settings
    app.state.session_factory = FakeSession
    app.add_middleware(RolePermissionMiddleware)
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: FakeSession()
    client = TestClient(app)
    body = {"reference": "order-1", "amount": 10000}
    assert client.post("/api/v1/payments", json=body).status_code == 401
    token = issue_token(user, settings, "access")
    response = client.post(
        "/api/v1/payments", json=body, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


def test_payment_idempotency_and_ownership_in_postgres(database_url):
    engine = build_engine(database_url)
    sessions = build_session_factory(engine)
    user_ids = [uuid4(), uuid4()]
    with sessions.begin() as session:
        session.add_all(
            [
                User(
                    id=user_id,
                    email=f"{user_id}@test.invalid",
                    full_name="Test",
                    password_hash="x",
                    role="member",
                )
                for user_id in user_ids
            ]
        )
    details = PaymentDetails(reference="order-1", amount=10000)
    try:

        def submit(_):
            with sessions() as session:
                payment, created = create_payment(session, user_ids[0], "same-key", details)
                return payment.id, created

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(submit, range(4)))
        assert len({item[0] for item in results}) == 1
        assert sum(item[1] for item in results) == 1
        payment_id = results[0][0]
        with sessions() as session:
            with pytest.raises(IdempotencyConflict):
                create_payment(session, user_ids[0], "same-key", PaymentDetails("other", 10000))
        with sessions() as session:
            assert get_payment(session, user_ids[1], payment_id) is None
        with sessions() as session:
            other, created = create_payment(session, user_ids[1], "same-key", details)
            assert created and other.id != payment_id
    finally:
        with sessions.begin() as session:
            session.execute(delete(Payment).where(Payment.user_id.in_(user_ids)))
            session.execute(delete(User).where(User.id.in_(user_ids)))
        engine.dispose()
