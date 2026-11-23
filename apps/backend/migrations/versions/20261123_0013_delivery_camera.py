"""Link CCTV cameras to Tuya and select one delivery camera per location.

Revision ID: 20261123_0013
Revises: 20261122_0012
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261123_0013"
down_revision = "20261122_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cctv_cameras", sa.Column("tuya_device_id", sa.String(100)))
    op.add_column(
        "cctv_cameras",
        sa.Column("is_delivery_camera", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index(
        "ix_cctv_cameras_delivery_location",
        "cctv_cameras",
        ["location_id"],
        unique=True,
        postgresql_where=sa.text("is_delivery_camera"),
    )
    op.create_unique_constraint(
        "cctv_cameras_tuya_device_id_key", "cctv_cameras", ["tuya_device_id"]
    )
    # Retain the original photo's access scope even if the location is deleted.
    op.add_column("shipment", sa.Column("photo_location_id", postgresql.UUID(as_uuid=True)))


def downgrade() -> None:
    op.drop_column("shipment", "photo_location_id")
    op.drop_constraint("cctv_cameras_tuya_device_id_key", "cctv_cameras", type_="unique")
    op.drop_index("ix_cctv_cameras_delivery_location", table_name="cctv_cameras")
    op.drop_column("cctv_cameras", "is_delivery_camera")
    op.drop_column("cctv_cameras", "tuya_device_id")
