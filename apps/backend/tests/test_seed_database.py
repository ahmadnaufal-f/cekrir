import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from cekrir.db.model import Location, User
from cekrir.db.session import build_engine
from cekrir.services.auth import verify_password

script = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "20261120_0007_seed_accounts_location.py"
)
spec = importlib.util.spec_from_file_location("seed_migration", script)
seeder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seeder)


def test_seed_creates_accounts_and_location_idempotently(database_url):
    engine = build_engine(database_url)
    suffix = uuid4().hex
    settings = {
        "admin_email": f"admin-{suffix}@example.test",
        "member_email": f"member-{suffix}@example.test",
        "location": f"Test location {suffix}",
        "admin_password": "admin-password-123",
        "member_password": "member-password-123",
    }
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                seeder.seed(connection, settings)
                seeder.seed(connection, settings)
                admin = connection.execute(
                    select(User.id, User.password_hash).where(User.email == settings["admin_email"])
                ).one()
                member = connection.execute(
                    select(User.id, User.password_hash).where(
                        User.email == settings["member_email"]
                    )
                ).one()
                location = connection.execute(
                    select(Location.admin_user_id).where(Location.name == settings["location"])
                ).one()
                assert verify_password(settings["admin_password"], admin.password_hash)
                assert verify_password(settings["member_password"], member.password_hash)
                assert location.admin_user_id == admin.id
                with pytest.raises(ValueError, match="different role"):
                    seeder.seed(
                        connection,
                        {
                            **settings,
                            "admin_email": settings["member_email"],
                            "member_email": f"other-{suffix}@example.test",
                        },
                    )
                with connection.begin_nested() as nested:
                    with pytest.raises(ValueError, match="CEKRIR_SEED_MEMBER_PASSWORD"):
                        seeder.seed(
                            connection,
                            {
                                **settings,
                                "admin_email": f"new-admin-{suffix}@example.test",
                                "member_email": f"new-member-{suffix}@example.test",
                                "member_password": None,
                            },
                        )
                    nested.rollback()
                assert connection.execute(
                    select(User.id).where(User.email == f"new-admin-{suffix}@example.test")
                ).first() is None
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
