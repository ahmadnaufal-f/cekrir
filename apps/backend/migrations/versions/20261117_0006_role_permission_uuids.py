"""Use UUID identifiers for roles and permissions.

Revision ID: 20261117_0006
Revises: 20261117_0005
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261117_0006"
down_revision = "20261117_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    for table in ("roles", "permissions"):
        op.add_column(
            table, sa.Column("id", uuid_type, server_default=sa.text("gen_random_uuid()"))
        )
        op.execute(f"UPDATE {table} SET id = gen_random_uuid() WHERE id IS NULL")
        op.alter_column(table, "id", nullable=False)

    op.add_column("cekrir_user", sa.Column("role_id", uuid_type))
    op.execute("UPDATE cekrir_user u SET role_id = r.id FROM roles r WHERE u.role = r.name")
    op.alter_column("cekrir_user", "role_id", nullable=False)

    op.add_column("role_permissions", sa.Column("role_id", uuid_type))
    op.add_column("role_permissions", sa.Column("permission_id", uuid_type))
    op.execute(
        "UPDATE role_permissions rp SET role_id = r.id FROM roles r WHERE rp.role_name = r.name"
    )
    op.execute(
        "UPDATE role_permissions rp SET permission_id = p.id "
        "FROM permissions p WHERE rp.permission_name = p.name"
    )
    op.alter_column("role_permissions", "role_id", nullable=False)
    op.alter_column("role_permissions", "permission_id", nullable=False)

    op.add_column("locations", sa.Column("admin_role_id", uuid_type))
    op.execute(
        "UPDATE locations l SET admin_role_id = u.role_id "
        "FROM cekrir_user u WHERE l.admin_user_id = u.id"
    )
    op.alter_column("locations", "admin_role_id", nullable=False)

    op.drop_constraint("locations_admin_user_role_fkey", "locations", type_="foreignkey")
    op.drop_index("cekrir_user_id_role_key", table_name="cekrir_user")
    op.drop_constraint("cekrir_user_role_fkey", "cekrir_user", type_="foreignkey")
    op.drop_constraint("role_permissions_role_name_fkey", "role_permissions", type_="foreignkey")
    op.drop_constraint(
        "role_permissions_permission_name_fkey", "role_permissions", type_="foreignkey"
    )
    op.drop_constraint("role_permissions_pkey", "role_permissions", type_="primary")
    op.drop_index("role_permissions_permission_name_idx", table_name="role_permissions")
    op.drop_column("role_permissions", "role_name")
    op.drop_column("role_permissions", "permission_name")
    op.drop_column("cekrir_user", "role")
    op.drop_constraint(op.f("ck_locations_admin_role"), "locations", type_="check")
    op.alter_column("locations", "admin_role", new_column_name="admin_role_code")

    for table in ("roles", "permissions"):
        op.drop_constraint(f"{table}_pkey", table, type_="primary")
        op.alter_column(table, "name", new_column_name="code")
        op.create_primary_key(f"{table}_pkey", table, ["id"])
        op.create_index(f"{table}_code_key", table, ["code"], unique=True)
    op.create_index("roles_id_code_key", "roles", ["id", "code"], unique=True)
    op.create_primary_key("role_permissions_pkey", "role_permissions", ["role_id", "permission_id"])
    op.create_foreign_key(
        "role_permissions_role_id_fkey",
        "role_permissions",
        "roles",
        ["role_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "role_permissions_permission_id_fkey",
        "role_permissions",
        "permissions",
        ["permission_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("role_permissions_permission_id_idx", "role_permissions", ["permission_id"])
    op.create_foreign_key(
        "cekrir_user_role_id_fkey", "cekrir_user", "roles", ["role_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index("cekrir_user_id_role_id_key", "cekrir_user", ["id", "role_id"], unique=True)
    op.create_check_constraint(
        op.f("ck_locations_admin_role_code"), "locations", "admin_role_code = 'admin'"
    )
    op.create_foreign_key(
        "locations_admin_user_role_id_fkey",
        "locations",
        "cekrir_user",
        ["admin_user_id", "admin_role_id"],
        ["id", "role_id"],
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "locations_admin_role_fkey",
        "locations",
        "roles",
        ["admin_role_id", "admin_role_code"],
        ["id", "code"],
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )


def downgrade() -> None:
    op.add_column("cekrir_user", sa.Column("role", sa.String(24)))
    op.execute("UPDATE cekrir_user u SET role = r.code FROM roles r WHERE u.role_id = r.id")
    op.alter_column("cekrir_user", "role", nullable=False, server_default=sa.text("'member'"))
    op.add_column("role_permissions", sa.Column("role_name", sa.String(24)))
    op.add_column("role_permissions", sa.Column("permission_name", sa.String(80)))
    op.execute(
        "UPDATE role_permissions rp SET role_name = r.code FROM roles r WHERE rp.role_id = r.id"
    )
    op.execute(
        "UPDATE role_permissions rp SET permission_name = p.code "
        "FROM permissions p WHERE rp.permission_id = p.id"
    )
    op.alter_column("role_permissions", "role_name", nullable=False)
    op.alter_column("role_permissions", "permission_name", nullable=False)

    op.drop_constraint("locations_admin_role_fkey", "locations", type_="foreignkey")
    op.drop_constraint("locations_admin_user_role_id_fkey", "locations", type_="foreignkey")
    op.drop_constraint(op.f("ck_locations_admin_role_code"), "locations", type_="check")
    op.drop_column("locations", "admin_role_id")
    op.alter_column("locations", "admin_role_code", new_column_name="admin_role")
    op.drop_index("cekrir_user_id_role_id_key", table_name="cekrir_user")
    op.drop_constraint("cekrir_user_role_id_fkey", "cekrir_user", type_="foreignkey")
    op.drop_column("cekrir_user", "role_id")
    op.drop_constraint("role_permissions_role_id_fkey", "role_permissions", type_="foreignkey")
    op.drop_constraint(
        "role_permissions_permission_id_fkey", "role_permissions", type_="foreignkey"
    )
    op.drop_constraint("role_permissions_pkey", "role_permissions", type_="primary")
    op.drop_index("role_permissions_permission_id_idx", table_name="role_permissions")
    op.drop_column("role_permissions", "role_id")
    op.drop_column("role_permissions", "permission_id")
    op.drop_index("roles_id_code_key", table_name="roles")
    for table in ("roles", "permissions"):
        op.drop_index(f"{table}_code_key", table_name=table)
        op.drop_constraint(f"{table}_pkey", table, type_="primary")
        op.alter_column(table, "code", new_column_name="name")
        op.create_primary_key(f"{table}_pkey", table, ["name"])
        op.drop_column(table, "id")
    op.create_primary_key(
        "role_permissions_pkey", "role_permissions", ["role_name", "permission_name"]
    )
    op.create_foreign_key(
        "role_permissions_role_name_fkey",
        "role_permissions",
        "roles",
        ["role_name"],
        ["name"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "role_permissions_permission_name_fkey",
        "role_permissions",
        "permissions",
        ["permission_name"],
        ["name"],
        ondelete="CASCADE",
    )
    op.create_index("role_permissions_permission_name_idx", "role_permissions", ["permission_name"])
    op.create_foreign_key(
        "cekrir_user_role_fkey", "cekrir_user", "roles", ["role"], ["name"], ondelete="RESTRICT"
    )
    op.create_index("cekrir_user_id_role_key", "cekrir_user", ["id", "role"], unique=True)
    op.create_check_constraint(op.f("ck_locations_admin_role"), "locations", "admin_role = 'admin'")
    op.create_foreign_key(
        "locations_admin_user_role_fkey",
        "locations",
        "cekrir_user",
        ["admin_user_id", "admin_role"],
        ["id", "role"],
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
