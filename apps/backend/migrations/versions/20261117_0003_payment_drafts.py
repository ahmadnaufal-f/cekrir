"""Create idempotent payment drafts.

Revision ID: 20261117_0003
Revises: 20261117_0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261117_0003"
down_revision = "20261117_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("reference", sa.String(128), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'IDR'")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True, precision=3),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "amount > 0 AND amount <= 10000000", name=op.f("ck_payment_amount_range")
        ),
        sa.CheckConstraint("currency = 'IDR'", name=op.f("ck_payment_currency_idr")),
        sa.CheckConstraint("status = 'draft'", name=op.f("ck_payment_status_draft")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["cekrir_user.id"], name="payment_user_id_fkey", ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "payment_user_idempotency_key_key", "payment", ["user_id", "idempotency_key"], unique=True
    )


def downgrade() -> None:
    op.drop_table("payment")
