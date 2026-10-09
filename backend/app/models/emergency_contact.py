from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    emergency_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    phone_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    jurisdiction: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    primary_source_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    primary_source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    secondary_source_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    secondary_source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )