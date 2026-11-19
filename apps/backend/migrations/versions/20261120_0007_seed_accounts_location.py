"""Seed a development administrator, member and administrator-owned location.

Revision ID: 20261120_0007
Revises: 20261117_0006
"""

import os
import re
from pathlib import Path

import bcrypt
import sqlalchemy as sa
from alembic import op
from dotenv import dotenv_values

revision = "20261120_0007"
down_revision = "20261117_0006"
branch_labels = None
depends_on = None


def seed_settings():
    backend = Path(__file__).resolve().parents[2]
    root = backend.parents[1]
    values = {}
    for file in (root / ".env", backend / ".env", backend / ".env.seed"):
        values.update(
            {key: value for key, value in dotenv_values(file).items() if value is not None}
        )
    values.update(os.environ)
    return {
        "admin_email": (
            values.get("CEKRIR_SEED_ADMIN_EMAIL")
            or values.get("CEKRIR_BOOTSTRAP_ADMIN_EMAIL")
            or "admin@example.test"
        )
        .strip()
        .lower(),
        "member_email": (values.get("CEKRIR_SEED_MEMBER_EMAIL") or "member@example.test")
        .strip()
        .lower(),
        "location": (values.get("CEKRIR_SEED_LOCATION") or "Main Location").strip(),
        "admin_password": values.get("CEKRIR_SEED_ADMIN_PASSWORD")
        or values.get("CEKRIR_BOOTSTRAP_ADMIN_PASSWORD"),
        "member_password": values.get("CEKRIR_SEED_MEMBER_PASSWORD"),
    }


def seed(connection, settings):
    """Create missing records without changing pre-existing users or locations."""
    admin_email, member_email = settings["admin_email"], settings["member_email"]
    if admin_email == member_email or any(
        len(email) > 320 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
        for email in (admin_email, member_email)
    ):
        raise ValueError("Seed admin and member must have different valid email addresses")
    if not settings["location"] or len(settings["location"]) > 200:
        raise ValueError("Seed location must contain 1 to 200 characters")

    users = {}
    for role, email, full_name in (
        ("admin", admin_email, "Development Admin"),
        ("member", member_email, "Development Member"),
    ):
        role_id = connection.execute(
            sa.text("SELECT id FROM roles WHERE code = :code"), {"code": role}
        ).scalar_one()
        user = connection.execute(
            sa.text("SELECT id, role_id FROM cekrir_user WHERE email = :email"), {"email": email}
        ).first()
        if user:
            if user.role_id != role_id:
                raise ValueError(f"The configured seed {role} email has a different role")
            users[role] = user.id
            continue
        password = settings[f"{role}_password"]
        if not password or len(password) < 12 or len(password.encode("utf-8")) > 72:
            raise ValueError(
                f"Set CEKRIR_SEED_{role.upper()}_PASSWORD to at least 12 characters "
                "and at most 72 UTF-8 bytes before running this migration"
            )
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
        users[role] = connection.execute(
            sa.text(
                "INSERT INTO cekrir_user (email, full_name, password_hash, role_id, "
                "email_verified_at) VALUES (:email, :full_name, :password_hash, :role_id, "
                "CURRENT_TIMESTAMP) RETURNING id"
            ),
            {"email": email, "full_name": full_name, "password_hash": hashed, "role_id": role_id},
        ).scalar_one()

    exists = connection.execute(
        sa.text("SELECT 1 FROM locations WHERE name = :name AND admin_user_id = :admin_id"),
        {"name": settings["location"], "admin_id": users["admin"]},
    ).first()
    if not exists:
        connection.execute(
            sa.text(
                "INSERT INTO locations (name, admin_user_id, admin_role_id, admin_role_code) "
                "SELECT :name, u.id, u.role_id, 'admin' FROM cekrir_user u WHERE u.id = :admin_id"
            ),
            {"name": settings["location"], "admin_id": users["admin"]},
        )


def upgrade() -> None:
    if op.get_context().as_sql:
        raise RuntimeError("The seed migration requires an online database connection")
    seed(op.get_bind(), seed_settings())


def downgrade() -> None:
    # The migration may have reused existing records. Never delete user data on downgrade.
    pass
