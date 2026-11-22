"""Keep unverified accounts inactive until their email is confirmed.

Revision ID: 20261122_0010
Revises: 20261121_0009
"""

import sqlalchemy as sa
from alembic import op

revision = "20261122_0010"
down_revision = "20261121_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("cekrir_user", "is_active", server_default=sa.text("false"))
    op.execute("UPDATE cekrir_user SET is_active = false WHERE email_verified_at IS NULL")


def downgrade() -> None:
    # Do not reactivate existing accounts; their previous status is unknown.
    op.alter_column("cekrir_user", "is_active", server_default=sa.text("true"))
