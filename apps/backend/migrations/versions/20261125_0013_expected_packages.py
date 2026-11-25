"""Save expected packages and their order details by location.

Revision ID: 20261125_0013
Revises: 20261122_0012
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261125_0013"
down_revision = "20261122_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shipment",
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "shipment_location_id_fkey",
        "shipment",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("shipment_location_id_idx", "shipment", ["location_id"])
    op.add_column("shipment", sa.Column("sender_name", sa.String(length=200), nullable=True))
    op.add_column(
        "shipment",
        sa.Column(
            "product_names",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_index("shipment_courier_resi_number_key", table_name="shipment")
    op.create_index(
        "shipment_courier_resi_number_key",
        "shipment",
        ["courier", "resi_number", "location_id"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_index("shipment_courier_resi_number_key", table_name="shipment")
    op.create_index(
        "shipment_courier_resi_number_key", "shipment", ["courier", "resi_number"], unique=True
    )
    op.drop_column("shipment", "product_names")
    op.drop_column("shipment", "sender_name")
    op.drop_index("shipment_location_id_idx", table_name="shipment")
    op.drop_constraint("shipment_location_id_fkey", "shipment", type_="foreignkey")
    op.drop_column("shipment", "location_id")
