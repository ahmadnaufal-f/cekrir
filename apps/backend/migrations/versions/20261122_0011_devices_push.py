"""Add ESP credentials, encrypted CCTV cameras, and location push registrations.

Revision ID: 20261122_0011
Revises: 20261122_0010
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261122_0011"
down_revision = "20261122_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("esp_devices", sa.Column("credential_hash", sa.String(64)))
    op.add_column(
        "esp_devices", sa.Column("last_seen_at", postgresql.TIMESTAMP(timezone=True, precision=3))
    )
    op.create_table(
        "cctv_cameras",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("stream_url_encrypted", sa.Text(), nullable=False),
        sa.Column("username_encrypted", sa.Text(), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
    )
    op.create_index("ix_cctv_cameras_location_id", "cctv_cameras", ["location_id"])
    op.create_table(
        "fcm_devices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cekrir_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_fcm_devices_user_id", "fcm_devices", ["user_id"])
    op.create_table(
        "fcm_device_locations",
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fcm_devices.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("fcm_device_locations")
    op.drop_table("fcm_devices")
    op.drop_table("cctv_cameras")
    op.drop_column("esp_devices", "last_seen_at")
    op.drop_column("esp_devices", "credential_hash")
