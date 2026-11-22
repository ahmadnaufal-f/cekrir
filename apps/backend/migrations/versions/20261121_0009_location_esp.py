"""Track the single ESP assigned to each location.

Revision ID: 20261121_0009
Revises: 20261121_0008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261121_0009"
down_revision = "20261121_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "esp_devices",
        sa.Column("device_id", sa.String(100), primary_key=True),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("esp_devices")
