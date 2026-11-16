"""Add full names to existing users.

Revision ID: 20261117_0002
Revises: 20261117_0001
"""

import sqlalchemy as sa
from alembic import op

revision = "20261117_0002"
down_revision = "20261117_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cekrir_user", sa.Column("full_name", sa.String(200), nullable=True))
    op.execute("UPDATE cekrir_user SET full_name = LEFT(email, 200) WHERE full_name IS NULL")
    op.alter_column("cekrir_user", "full_name", nullable=False)


def downgrade() -> None:
    op.drop_column("cekrir_user", "full_name")
