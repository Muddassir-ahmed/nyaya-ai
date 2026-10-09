from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "jurisdictions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="IN",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    parent: Mapped["Jurisdiction | None"] = relationship(
        "Jurisdiction",
        remote_side=[id],
        back_populates="children",
    )

    children: Mapped[list["Jurisdiction"]] = relationship(
        "Jurisdiction",
        back_populates="parent",
    )