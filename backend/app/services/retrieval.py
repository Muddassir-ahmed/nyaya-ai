from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.act import Act
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument
from app.models.legal_version import LegalVersion
from app.services.embeddings import get_embedding_provider


async def search_legal_chunks(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    act_id: int | None = None,
    version_id: int | None = None,
    jurisdiction_id: int | None = None,
    source_id: int | None = None,
    effective_date: date | None = None,
) -> list[LegalChunk]:

    if not query.strip():
        raise ValueError("Query cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    embedding_provider = get_embedding_provider()

    query_embedding = await embedding_provider.embed_text(query)

    distance = LegalChunk.embedding.cosine_distance(
        query_embedding
    )

    query_stmt = (
        select(LegalChunk)
        .join(
            LegalDocument,
            LegalChunk.document_id == LegalDocument.id,
        )
        .join(
            Act,
            LegalChunk.act_id == Act.id,
            isouter=True,
        )
        .join(
            LegalVersion,
            LegalChunk.version_id == LegalVersion.id,
            isouter=True,
        )
        .where(
            LegalChunk.embedding.is_not(None)
        )
    )

    if act_id is not None:
        query_stmt = query_stmt.where(
            LegalChunk.act_id == act_id
        )

    if version_id is not None:
        query_stmt = query_stmt.where(
            LegalChunk.version_id == version_id
        )

    if jurisdiction_id is not None:
        query_stmt = query_stmt.where(
            Act.jurisdiction_id == jurisdiction_id
        )

    if source_id is not None:
        query_stmt = query_stmt.where(
            LegalDocument.source_id == source_id
        )

    if effective_date is not None:
        query_stmt = query_stmt.where(
            LegalVersion.effective_from <= effective_date,
            (
                LegalVersion.effective_until.is_(None)
                | (
                    LegalVersion.effective_until
                    >= effective_date
                )
            ),
        )

    result = await db.execute(
        query_stmt
        .order_by(distance)
        .limit(top_k)
    )

    return list(result.scalars().all())