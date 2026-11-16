from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from cekrir.db.model.base import Base


class Role(Base):
    __tablename__ = "roles"

    __table_args__ = (
        Index("roles_code_key", "code", unique=True),
        Index("roles_id_code_key", "id", "code", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(24), nullable=False)


class Permission(Base):
    __tablename__ = "permissions"

    __table_args__ = (Index("permissions_code_key", "code", unique=True),)

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (Index("role_permissions_permission_id_idx", "permission_id"),)

    role_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
