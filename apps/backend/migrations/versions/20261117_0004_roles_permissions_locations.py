"""Create roles, permissions and locations.

Revision ID: 20261117_0004
Revises: 20261117_0003
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261117_0004"
down_revision = "20261117_0003"
branch_labels = None
depends_on = None

PERMISSIONS = (
    "shipments:read",
    "shipments:create",
    "shipments:refresh",
    "detections:create",
    "notifications:read",
    "payments:read",
    "payments:create",
    "users:read",
    "users:role:update",
)
MEMBER_PERMISSIONS = (
    "shipments:read",
    "shipments:create",
    "notifications:read",
    "payments:read",
    "payments:create",
)


def upgrade() -> None:
    op.create_table("roles", sa.Column("name", sa.String(24), primary_key=True))
    op.create_table("permissions", sa.Column("name", sa.String(80), primary_key=True))
    op.create_table(
        "role_permissions",
        sa.Column(
            "role_name",
            sa.String(24),
            sa.ForeignKey("roles.name", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_name",
            sa.String(80),
            sa.ForeignKey("permissions.name", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("role_permissions_permission_name_idx", "role_permissions", ["permission_name"])
    op.bulk_insert(
        sa.table("roles", sa.column("name", sa.String())), [{"name": "admin"}, {"name": "member"}]
    )
    op.bulk_insert(
        sa.table("permissions", sa.column("name", sa.String())),
        [{"name": name} for name in PERMISSIONS],
    )
    associations = [{"role_name": "admin", "permission_name": name} for name in PERMISSIONS]
    associations += [
        {"role_name": "member", "permission_name": name} for name in MEMBER_PERMISSIONS
    ]
    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role_name", sa.String()),
            sa.column("permission_name", sa.String()),
        ),
        associations,
    )

    op.execute("ALTER TABLE cekrir_user DROP CONSTRAINT IF EXISTS ck_cekrir_user_role_values")
    op.execute(
        "ALTER TABLE cekrir_user DROP CONSTRAINT IF EXISTS "
        "ck_cekrir_user_ck_cekrir_user_role_values"
    )
    op.create_foreign_key(
        "cekrir_user_role_fkey", "cekrir_user", "roles", ["role"], ["name"], ondelete="RESTRICT"
    )
    op.create_index("cekrir_user_id_role_key", "cekrir_user", ["id", "role"], unique=True)
    op.create_table(
        "locations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_role", sa.String(24), nullable=False, server_default=sa.text("'admin'")),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True, precision=3),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("admin_role = 'admin'", name=op.f("ck_locations_admin_role")),
        sa.ForeignKeyConstraint(
            ["admin_user_id", "admin_role"],
            ["cekrir_user.id", "cekrir_user.role"],
            name="locations_admin_user_role_fkey",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
    )
    op.create_index("locations_admin_user_id_idx", "locations", ["admin_user_id"])


def downgrade() -> None:
    op.drop_table("locations")
    op.drop_index("cekrir_user_id_role_key", table_name="cekrir_user")
    op.drop_constraint("cekrir_user_role_fkey", "cekrir_user", type_="foreignkey")
    op.create_check_constraint(
        op.f("ck_cekrir_user_role_values"), "cekrir_user", "role IN ('admin', 'member')"
    )
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
