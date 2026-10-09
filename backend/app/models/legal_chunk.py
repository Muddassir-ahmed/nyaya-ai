from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import TSVECTOR
from datetime import datetime

from pgvector.sqlalchemy import Vector

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LegalChunk(Base):
    __tablename__ = "legal_chunks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "legal_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    act_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "acts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "legal_versions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    section_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "sections.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    subsection_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "subsections.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    clause_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "clauses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    search_vector: Mapped[str | None] = mapped_column(
    TSVECTOR,
    Computed(
        "to_tsvector('english', content)",
        persisted=True,
    ),
        nullable=True,

    )

    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
