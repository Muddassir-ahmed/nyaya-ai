from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Subsection(Base):
    __tablename__ = "subsections"

    __table_args__ = (
        UniqueConstraint(
            "section_id",
            "subsection_number",
            name="uq_subsection_section_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    section_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sections.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    subsection_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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