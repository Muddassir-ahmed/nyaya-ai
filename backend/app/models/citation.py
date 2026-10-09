from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    section_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "sections.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey(
            "legal_sources.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    citation_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    source_location: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    verification_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )