from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from cekrir.db.model import Location, Permission, Role, RolePermission, User
from cekrir.db.session import build_engine, build_session_factory


def test_roles_and_permissions_have_uuid_identifiers():
    role_id, permission_id = uuid4(), uuid4()
    role = Role(id=role_id, code="admin")
    permission = Permission(id=permission_id, code="users:read")
    association = RolePermission(role_id=role.id, permission_id=permission.id)
    user = User(role_record=role)
    assert user.role == "admin"
    assert (association.role_id, association.permission_id) == (role_id, permission_id)


def test_location_admin_and_role_permissions_in_postgres(database_url):
    engine = build_engine(database_url)
    sessions = build_session_factory(engine)
    admin_id, member_id = uuid4(), uuid4()
    try:
        with sessions.begin() as session:
            admin_role = session.scalar(select(Role).where(Role.code == "admin"))
            member_role = session.scalar(select(Role).where(Role.code == "member"))
            session.add_all(
                [
                    User(
                        id=admin_id,
                        email=f"{admin_id}@test.invalid",
                        full_name="Admin",
                        password_hash="x",
                        role_record=admin_role,
                    ),
                    User(
                        id=member_id,
                        email=f"{member_id}@test.invalid",
                        full_name="Member",
                        password_hash="x",
                        role_record=member_role,
                    ),
                ]
            )
        with sessions.begin() as session:
            admin_role = session.scalar(select(Role).where(Role.code == "admin"))
            member_role = session.scalar(select(Role).where(Role.code == "member"))
            permission = session.scalar(
                select(Permission).where(Permission.code == "users:role:update")
            )
            assert session.get(RolePermission, (admin_role.id, permission.id)) is not None
            assert session.get(RolePermission, (member_role.id, permission.id)) is None
            admin = session.get(User, admin_id)
            session.add_all(
                [
                    Location(name="Home", admin=admin),
                    Location(name="Office", admin=admin),
                ]
            )
        with pytest.raises(IntegrityError), sessions.begin() as session:
            session.add(Location(name="Invalid", admin=session.get(User, member_id)))
        with pytest.raises(IntegrityError), sessions.begin() as session:
            session.get(User, admin_id).role_record = session.scalar(
                select(Role).where(Role.code == "member")
            )
    finally:
        with sessions.begin() as session:
            session.execute(
                delete(Location).where(Location.admin_user_id.in_([admin_id, member_id]))
            )
            session.execute(delete(User).where(User.id.in_([admin_id, member_id])))
        engine.dispose()
