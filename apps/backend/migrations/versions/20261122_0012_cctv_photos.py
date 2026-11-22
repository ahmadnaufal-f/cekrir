"""Track CCTV photo capture per shipment.

Revision ID: 20261122_0012
Revises: 20261122_0011
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261122_0012"
down_revision = "20261122_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shipment",
        sa.Column(
            "photo_status", sa.String(length=20), server_default="not_requested", nullable=False
        ),
    )
    op.add_column(
        "shipment", sa.Column("photo_captured_at", postgresql.TIMESTAMP(timezone=True, precision=3))
    )
    op.create_check_constraint(
        "shipment_photo_status_check",
        "shipment",
        "photo_status IN ('not_requested', 'pending', 'ready', 'unavailable')",
    )


def downgrade() -> None:
    op.drop_constraint("shipment_photo_status_check", "shipment", type_="check")
    op.drop_column("shipment", "photo_captured_at")
    op.drop_column("shipment", "photo_status")
