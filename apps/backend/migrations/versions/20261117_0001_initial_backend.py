"""Create the ORM-managed schema and auth users table.

Revision ID: 20261117_0001
Revises:
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261117_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_enum_if_missing(name: str, values: tuple[str, ...]) -> None:
    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(
        f'''DO $$ BEGIN
            CREATE TYPE "{name}" AS ENUM ({values_sql});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;'''
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    _create_enum_if_missing("ShipmentStatus", ("pending", "in_transit", "delivered", "exception"))
    _create_enum_if_missing("ShipmentSource", ("manual", "camera"))

    status_enum = postgresql.ENUM(
        "pending", "in_transit", "delivered", "exception", name="ShipmentStatus", create_type=False
    )
    source_enum = postgresql.ENUM("manual", "camera", name="ShipmentSource", create_type=False)

    if "shipment" not in tables:
        op.create_table(
            "shipment",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("resi_number", sa.String(length=64), nullable=False),
            sa.Column("courier", sa.String(length=32), nullable=False),
            sa.Column("source", source_enum, nullable=False),
            sa.Column("camera_id", sa.String(length=100), nullable=True),
            sa.Column("status", status_enum, nullable=False, server_default=sa.text("'pending'")),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("provider", sa.Text(), nullable=False),
            sa.Column(
                "history",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "created_at",
                postgresql.TIMESTAMP(precision=3, timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "checked_at",
                postgresql.TIMESTAMP(precision=3, timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "last_detected_at", postgresql.TIMESTAMP(precision=3, timezone=True), nullable=True
            ),
            sa.PrimaryKeyConstraint("id", name="shipment_pkey"),
        )
    shipment_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("shipment")}
    if "shipment_resi_number_idx" not in shipment_indexes:
        op.create_index("shipment_resi_number_idx", "shipment", ["resi_number"], unique=False)
    if "shipment_created_at_id_idx" not in shipment_indexes:
        op.create_index(
            "shipment_created_at_id_idx",
            "shipment",
            [sa.text("created_at DESC"), sa.text("id DESC")],
            unique=False,
        )
    if "shipment_courier_resi_number_key" not in shipment_indexes:
        op.create_index(
            "shipment_courier_resi_number_key", "shipment", ["courier", "resi_number"], unique=True
        )

    if "notification" not in tables:
        op.create_table(
            "notification",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                postgresql.TIMESTAMP(precision=3, timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["shipment_id"],
                ["shipment.id"],
                name="notification_shipment_id_fkey",
                ondelete="CASCADE",
                onupdate="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="notification_pkey"),
        )
    notification_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("notification")}
    if "notification_shipment_id_idx" not in notification_indexes:
        op.create_index(
            "notification_shipment_id_idx", "notification", ["shipment_id"], unique=False
        )
    if "notification_created_at_id_idx" not in notification_indexes:
        op.create_index(
            "notification_created_at_id_idx",
            "notification",
            [sa.text("created_at DESC"), sa.text("id DESC")],
            unique=False,
        )

    if "cekrir_user" not in tables:
        op.create_table(
            "cekrir_user",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column(
                "role", sa.String(length=24), nullable=False, server_default=sa.text("'member'")
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "created_at",
                postgresql.TIMESTAMP(precision=3, timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.CheckConstraint("role IN ('admin', 'member')", name="ck_cekrir_user_role_values"),
            sa.PrimaryKeyConstraint("id", name="cekrir_user_pkey"),
        )
    user_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("cekrir_user")}
    if "cekrir_user_email_key" not in user_indexes:
        op.create_index("cekrir_user_email_key", "cekrir_user", ["email"], unique=True)


def downgrade() -> None:
    # Shipment and notification predate the Python ORM. Keep those tables and their data.
    op.drop_table("cekrir_user")
