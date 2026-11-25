from uuid import uuid4

from sqlalchemy import select

from cekrir.db.model import Location, LocationMember, Role, User
from cekrir.services.auth import issue_token

EXPECTED = "/api/v1/shipments/expected"


def test_expected_package_details_are_persisted_and_visible_only_to_the_household(client, provider):
    settings = client.app.state.settings
    sessions = client.app.state.session_factory
    with sessions.begin() as session:
        owner = session.scalar(select(User).where(User.email == "seed-admin@example.test"))
        other = session.scalar(select(User).where(User.email == settings.bootstrap_admin_email))
        location = session.scalar(select(Location).where(Location.admin_user_id == owner.id))
        member = User(
            email=f"expected-package-{uuid4()}@example.test",
            full_name="Receiving location member",
            password_hash="unused by token test",
            role_record=session.scalar(select(Role).where(Role.code == "member")),
            is_active=True,
            email_verified_at=owner.email_verified_at,
        )
        session.add(member)
        session.flush()
        session.add(LocationMember(location_id=location.id, user_id=member.id))
        owner_auth, member_auth, other_auth = (
            {"Authorization": f"Bearer {issue_token(user, settings, 'access')}"}
            for user in (owner, member, other)
        )

    payload = {
        "courier": "spx",
        "resi_number": "000SPX-TEST",
        "sender_name": " Toko Contoh ",
        "product_names": [" Kotak penyimpanan ", "Keset meja"],
    }
    assert client.post(EXPECTED, json=payload, headers=other_auth).status_code == 409
    response = client.post(EXPECTED, json=payload, headers=member_auth)
    assert response.status_code == 201
    package = response.json()
    assert package["status"] == "pending"
    assert package["sender_name"] == "Toko Contoh"
    assert package["product_names"] == ["Kotak penyimpanan", "Keset meja"]
    assert provider.calls == 0

    detail_path = f"/api/v1/shipments/{package['id']}"
    assert client.get(detail_path, headers=owner_auth).json() == package
    assert client.get(detail_path, headers=other_auth).status_code == 404
    assert client.post(f"{detail_path}/refresh", headers=other_auth).status_code == 404
    assert client.get("/api/v1/shipments", headers=other_auth).json() == []
    assert client.get("/api/v1/shipments", headers=member_auth).json() == [package]

    duplicate = client.post(EXPECTED, json=payload, headers=owner_auth)
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == package["id"]
    assert (
        client.post(EXPECTED, json={**payload, "courier": "jne"}, headers=member_auth).status_code
        == 422
    )

    with sessions.begin() as session:
        other = session.scalar(select(User).where(User.email == settings.bootstrap_admin_email))
        session.add(Location(name="Other receiving location", admin=other))

    other_response = client.post(
        EXPECTED,
        json={"courier": "spx", "resi_number": payload["resi_number"]},
        headers=other_auth,
    )
    assert other_response.status_code == 201
    other_package = other_response.json()
    assert other_package["id"] != package["id"]
    assert other_package["sender_name"] is None and other_package["product_names"] == []
    assert client.get("/api/v1/shipments", headers=other_auth).json() == [other_package]
