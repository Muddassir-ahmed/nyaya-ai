"""finalize emergency contact provenance

Revision ID: 4d5f0f197ff9
Revises: d26db0a618e4
Create Date: 2026-09-07 20:26:35.475924
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d5f0f197ff9"
down_revision: Union[str, Sequence[str], None] = "d26db0a618e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Restore the GIN index accidentally removed by the
    # emergency_contacts migration.
    op.create_index(
        "ix_legal_chunks_search_vector",
        "legal_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )

    # Replace the old ambiguous single-source provenance fields
    # with explicit primary and secondary source provenance.
    op.add_column(
        "emergency_contacts",
        sa.Column(
            "primary_source_name",
            sa.String(length=300),
            nullable=False,
        ),
    )

    op.add_column(
        "emergency_contacts",
        sa.Column(
            "primary_source_url",
            sa.Text(),
            nullable=False,
        ),
    )

    op.add_column(
        "emergency_contacts",
        sa.Column(
            "secondary_source_name",
            sa.String(length=300),
            nullable=True,
        ),
    )

    op.add_column(
        "emergency_contacts",
        sa.Column(
            "secondary_source_url",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "emergency_contacts",
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "emergency_contacts",
        sa.Column(
            "verification_notes",
            sa.Text(),
            nullable=True,
        ),
    )

    # The table contains no production records at this point,
    # so the legacy fields can safely be removed.
    op.drop_column(
        "emergency_contacts",
        "source_name",
    )

    op.drop_column(
        "emergency_contacts",
        "source_url",
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Restore the legacy provenance fields.
    op.add_column(
        "emergency_contacts",
        sa.Column(
            "source_name",
            sa.String(length=300),
            nullable=True,
        ),
    )

    op.add_column(
        "emergency_contacts",
        sa.Column(
            "source_url",
            sa.Text(),
            nullable=True,
        ),
    )

    # Remove the new provenance fields.
    op.drop_column(
        "emergency_contacts",
        "verification_notes",
    )

    op.drop_column(
        "emergency_contacts",
        "verified_at",
    )

    op.drop_column(
        "emergency_contacts",
        "secondary_source_url",
    )

    op.drop_column(
        "emergency_contacts",
        "secondary_source_name",
    )

    op.drop_column(
        "emergency_contacts",
        "primary_source_url",
    )

    op.drop_column(
        "emergency_contacts",
        "primary_source_name",
    )

    # Remove the restored legal-chunk index.
    op.drop_index(
        "ix_legal_chunks_search_vector",
        table_name="legal_chunks",
    )