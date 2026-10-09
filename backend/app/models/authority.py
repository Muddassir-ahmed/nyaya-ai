from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Authority(Base):
    __tablename__ = "authorities"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # Human-readable authority name.
    # Example: Assam Police
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Broad organization type.
    # Examples:
    # police, cybercrime, consumer, labour, transport
    authority_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Legal/civic domain used for routing.
    # Examples:
    # criminal, cybercrime, consumer, employment
    domain: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Stable machine-readable routing identifier.
    # Example:
    # police_complaint
    service_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Human-readable service name.
    service_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Normalized jurisdiction.
    jurisdiction_id: Mapped[int] = mapped_column(
        ForeignKey(
            "jurisdictions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    official_portal_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    complaint_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # -----------------------------
    # Verification / provenance
    # -----------------------------

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

    # Lower value = preferred authority when multiple records
    # match the same service and jurisdiction.
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
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

    jurisdiction = relationship(
        "Jurisdiction",
    )