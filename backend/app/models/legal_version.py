from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LegalVersion(Base):
    __tablename__ = "legal_versions"

    __table_args__ = (
        CheckConstraint(
            "effective_until IS NULL OR effective_until >= effective_from",
            name="ck_legal_version_dates",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    act_id: Mapped[int] = mapped_column(
        ForeignKey(
            "acts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    version_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    effective_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
    )

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "legal_sources.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
