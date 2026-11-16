from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from cekrir.db.model import Location, RolePermission, User
from cekrir.db.session import build_engine, build_session_factory


def test_location_admin_and_role_permissions_in_postgres(database_url):
    engine = build_engine(database_url)
    sessions = build_session_factory(engine)
    admin_id, member_id = uuid4(), uuid4()
    try:
        with sessions.begin() as session:
            session.add_all(
                [
                    User(
                        id=admin_id,
                        email=f"{admin_id}@test.invalid",
                        full_name="Admin",
                        password_hash="x",
                        role="admin",
                    ),
                    User(
                        id=member_id,
                        email=f"{member_id}@test.invalid",
                        full_name="Member",
                        password_hash="x",
                        role="member",
                    ),
                ]
            )
        with sessions.begin() as session:
            assert session.get(RolePermission, ("admin", "users:role:update")) is not None
            assert session.get(RolePermission, ("member", "users:role:update")) is None
            session.add_all(
                [
                    Location(name="Home", admin_user_id=admin_id),
                    Location(name="Office", admin_user_id=admin_id),
                ]
            )
        with pytest.raises(IntegrityError), sessions.begin() as session:
            session.add(Location(name="Invalid", admin_user_id=member_id))
        with pytest.raises(IntegrityError), sessions.begin() as session:
            session.get(User, admin_id).role = "member"
    finally:
        with sessions.begin() as session:
            session.execute(
                delete(Location).where(Location.admin_user_id.in_([admin_id, member_id]))
            )
            session.execute(delete(User).where(User.id.in_([admin_id, member_id])))
        engine.dispose()
