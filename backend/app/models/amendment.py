from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Amendment(Base):
    __tablename__ = "amendments"

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

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "legal_sources.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    amendment_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    amendment_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    enacted_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    effective_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
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