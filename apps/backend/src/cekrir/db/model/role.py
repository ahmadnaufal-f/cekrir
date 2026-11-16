from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from cekrir.db.model.base import Base


class Role(Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(24), primary_key=True)


class Permission(Base):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(80), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (Index("role_permissions_permission_name_idx", "permission_name"),)

    role_name: Mapped[str] = mapped_column(
        String(24), ForeignKey("roles.name", ondelete="CASCADE"), primary_key=True
    )
    permission_name: Mapped[str] = mapped_column(
        String(80), ForeignKey("permissions.name", ondelete="CASCADE"), primary_key=True
    )
