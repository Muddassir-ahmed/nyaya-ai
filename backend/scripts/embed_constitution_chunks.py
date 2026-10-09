from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument
from app.services.embeddings import get_embedding_provider


DOCUMENT_TITLE = "The Constitution of India"
DOCUMENT_TYPE = "constitution"

EXPECTED_SHA256 = (
    "4C8E93689EC245E26DB08E22B5FF3AD"
    "645C98736F0E5B7C8B6638ACD7861F85B"
)

EXPECTED_DIMENSION = 768

BATCH_SIZE = 32


async def get_constitution_document(
    db: AsyncSession,
) -> LegalDocument:
    result = await db.execute(
        select(LegalDocument)
        .where(
            LegalDocument.title
            == DOCUMENT_TITLE,

            LegalDocument.document_type
            == DOCUMENT_TYPE,
        )
    )

    documents = (
        result.scalars().all()
    )

    if len(documents) != 1:
        raise RuntimeError(
            "Expected exactly one canonical "
            "Constitution document, found "
            f"{len(documents)}."
        )

    document = documents[0]

    if not document.is_verified:
        raise RuntimeError(
            "Canonical Constitution document "
            "is not verified."
        )

    if (
        document.file_hash
        != EXPECTED_SHA256
    ):
        raise RuntimeError(
            "Constitution document hash does "
            "not match the locked source.\n"
            f"Expected: {EXPECTED_SHA256}\n"
            f"Found:    {document.file_hash}"
        )

    return document


async def count_constitution_chunks(
    db: AsyncSession,
    document_id: int,
) -> int:
    result = await db.execute(
        select(
            func.count(
                LegalChunk.id
            )
        )
        .where(
            LegalChunk.document_id
            == document_id
        )
    )

    return int(
        result.scalar_one()
    )


async def count_unembedded_chunks(
    db: AsyncSession,
    document_id: int,
) -> int:
    result = await db.execute(
        select(
            func.count(
                LegalChunk.id
            )
        )
        .where(
            LegalChunk.document_id
            == document_id,

            LegalChunk.embedding.is_(
                None
            ),
        )
    )

    return int(
        result.scalar_one()
    )


async def embed_constitution_chunks() -> None:
    # Uses the currently configured embedding
    # provider.
    #
    # For your NyayaAI configuration this should
    # resolve to the local Ollama embedding
    # provider using nomic-embed-text.
    provider = get_embedding_provider()

    async with AsyncSessionLocal() as db:

        document = (
            await get_constitution_document(
                db
            )
        )

        total_chunks = (
            await count_constitution_chunks(
                db,
                document.id,
            )
        )

        if total_chunks == 0:
            raise RuntimeError(
                "No Constitution chunks found. "
                "Run create_constitution_chunks "
                "first."
            )

        remaining = (
            await count_unembedded_chunks(
                db,
                document.id,
            )
        )

        already_embedded = (
            total_chunks
            - remaining
        )

        print(
            "================================"
        )
        print(
            "Constitution embedding job"
        )
        print(
            "================================"
        )

        print(
            f"Document ID: "
            f"{document.id}"
        )

        print(
            f"Total Constitution chunks: "
            f"{total_chunks}"
        )

        print(
            f"Already embedded: "
            f"{already_embedded}"
        )

        print(
            f"Remaining: "
            f"{remaining}"
        )

        print(
            f"Batch size: "
            f"{BATCH_SIZE}"
        )

        print(
            f"Expected dimension: "
            f"{EXPECTED_DIMENSION}"
        )

        print(
            "Provider: "
            f"{provider.__class__.__name__}"
        )

        if remaining == 0:
            print(
                "\nAll Constitution chunks "
                "are already embedded."
            )
            return

        # -----------------------------------------
        # Load ONLY Constitution chunks that
        # currently have no embedding.
        #
        # This deliberately avoids the problem in
        # the older embed_bns_chunks.py script,
        # which selected all unembedded chunks.
        # -----------------------------------------

        result = await db.execute(
            select(LegalChunk)
            .where(
                LegalChunk.document_id
                == document.id,

                LegalChunk.embedding.is_(
                    None
                ),
            )
            .order_by(
                LegalChunk.id
            )
        )

        chunks = (
            result.scalars().all()
        )

        if len(chunks) != remaining:
            raise RuntimeError(
                "Unembedded Constitution chunk "
                "count changed unexpectedly.\n"
                f"Expected: {remaining}\n"
                f"Loaded:   {len(chunks)}"
            )

        processed = 0

        for start in range(
            0,
            len(chunks),
            BATCH_SIZE,
        ):
            batch = chunks[
                start:
                start + BATCH_SIZE
            ]

            texts = [
                chunk.content
                for chunk in batch
            ]

            first_number = (
                start + 1
            )

            last_number = (
                start
                + len(batch)
            )

            print(
                "\nEmbedding Constitution "
                f"chunks {first_number}-"
                f"{last_number} "
                f"of {len(chunks)}..."
            )

            try:
                embeddings = (
                    await provider.embed_texts(
                        texts
                    )
                )

                if (
                    len(embeddings)
                    != len(batch)
                ):
                    raise RuntimeError(
                        "Embedding provider "
                        "returned the wrong "
                        "number of vectors.\n"
                        f"Texts: "
                        f"{len(batch)}\n"
                        f"Vectors: "
                        f"{len(embeddings)}"
                    )

                for (
                    chunk,
                    embedding,
                ) in zip(
                    batch,
                    embeddings,
                ):

                    if (
                        len(embedding)
                        != EXPECTED_DIMENSION
                    ):
                        raise RuntimeError(
                            "Unexpected embedding "
                            "dimension for "
                            f"chunk {chunk.id}.\n"
                            f"Expected: "
                            f"{EXPECTED_DIMENSION}\n"
                            f"Found: "
                            f"{len(embedding)}"
                        )

                    chunk.embedding = (
                        embedding
                    )

                # Commit each batch so the job
                # is resumable if Ollama or the
                # process stops halfway through.
                await db.commit()

            except Exception:
                await db.rollback()
                raise

            processed += len(batch)

            print(
                f"Saved "
                f"{processed}/"
                f"{len(chunks)} "
                "new embeddings."
            )

        # -----------------------------------------
        # Final scoped verification
        # -----------------------------------------

        remaining_after = (
            await count_unembedded_chunks(
                db,
                document.id,
            )
        )

        total_after = (
            await count_constitution_chunks(
                db,
                document.id,
            )
        )

        if remaining_after != 0:
            raise RuntimeError(
                "Embedding job completed but "
                f"{remaining_after} Constitution "
                "chunks remain unembedded."
            )

        if (
            total_after
            != total_chunks
        ):
            raise RuntimeError(
                "Constitution chunk count "
                "changed during embedding.\n"
                f"Before: {total_chunks}\n"
                f"After:  {total_after}"
            )

    print(
        "\n================================"
    )

    print(
        "Constitution embeddings complete."
    )

    print(
        "================================"
    )

    print(
        f"New embeddings created: "
        f"{processed}"
    )

    print(
        f"Total embedded Constitution "
        f"chunks: {total_chunks}"
    )

    print(
        f"Vector dimension: "
        f"{EXPECTED_DIMENSION}"
    )


if __name__ == "__main__":
    asyncio.run(
        embed_constitution_chunks()
    )