"""Add email verification.

Revision ID: 20261117_0005
Revises: 20261117_0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261117_0005"
down_revision = "20261117_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cekrir_user",
        sa.Column("email_verified_at", postgresql.TIMESTAMP(timezone=True, precision=3)),
    )
    # Existing accounts predate verification; retain their access during the transition.
    op.execute("UPDATE cekrir_user SET email_verified_at = CURRENT_TIMESTAMP")
    op.create_table(
        "email_verification",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["cekrir_user.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("email_verification")
    op.drop_column("cekrir_user", "email_verified_at")
