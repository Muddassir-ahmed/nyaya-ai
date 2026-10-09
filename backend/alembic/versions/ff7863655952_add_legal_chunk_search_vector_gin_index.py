"""add legal chunk search vector gin index

Revision ID: REPLACE_ME
Revises: c21cbaced14e
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ff7863655952"
down_revision: Union[str, Sequence[str], None] = "c21cbaced14e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_legal_chunks_search_vector",
        "legal_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legal_chunks_search_vector",
        table_name="legal_chunks",
    )