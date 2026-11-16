from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cekrir.db.model.base import Base

if TYPE_CHECKING:
    from cekrir.db.model.user import User


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("admin_role = 'admin'", name="admin_role"),
        ForeignKeyConstraint(
            ["admin_user_id", "admin_role"],
            ["cekrir_user.id", "cekrir_user.role"],
            name="locations_admin_user_role_fkey",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index("locations_admin_user_id_idx", "admin_user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    admin_user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    admin_role: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default=text("'admin'")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    admin: Mapped[User] = relationship(back_populates="locations")
