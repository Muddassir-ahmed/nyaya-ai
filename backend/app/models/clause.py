from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Clause(Base):
    __tablename__ = "clauses"

    __table_args__ = (
        UniqueConstraint(
            "subsection_id",
            "clause_number",
            name="uq_clause_subsection_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    subsection_id: Mapped[int] = mapped_column(
        ForeignKey(
            "subsections.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    clause_number: Mapped[str] = mapped_column(
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