"""Associate location members and cameras and grant admin management permissions.

Revision ID: 20261121_0008
Revises: 20261120_0007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261121_0008"
down_revision = "20261120_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "location_members",
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cekrir_user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("location_members_user_id_idx", "location_members", ["user_id"])
    op.create_table(
        "camera_devices",
        sa.Column("camera_id", sa.String(100), primary_key=True),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("camera_devices_location_id_idx", "camera_devices", ["location_id"])
    op.add_column("notification", sa.Column("location_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "notification_location_id_fkey",
        "notification",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "INSERT INTO permissions (code) VALUES ('locations:manage'), ('notifications:send') "
        "ON CONFLICT (code) DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT roles.id, permissions.id FROM roles CROSS JOIN permissions "
        "WHERE roles.code = 'admin' "
        "AND permissions.code IN ('locations:manage', 'notifications:send') "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_constraint("notification_location_id_fkey", "notification", type_="foreignkey")
    op.drop_column("notification", "location_id")
    op.drop_table("camera_devices")
    op.drop_table("location_members")
    op.execute("DELETE FROM permissions WHERE code IN ('locations:manage', 'notifications:send')")
