from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cekrir.db.model.base import Base

if TYPE_CHECKING:
    from cekrir.db.model.location import Location


class User(Base):
    __tablename__ = "cekrir_user"
    __table_args__ = (
        Index("cekrir_user_email_key", "email", unique=True),
        Index("cekrir_user_id_role_key", "id", "role", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(24),
        ForeignKey("roles.name", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'member'"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    email_verified_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True, precision=3)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    locations: Mapped[list[Location]] = relationship(back_populates="admin", passive_deletes=True)
