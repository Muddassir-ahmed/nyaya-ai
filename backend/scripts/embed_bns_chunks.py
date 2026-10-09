import asyncio

from sqlalchemy import func, or_, select

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk
from app.services.embeddings import (
    get_embedding_provider,
)


BATCH_SIZE = 32

BNS_DOCUMENT_ID = 2
BNS_ACT_ID = 1
BNS_VERSION_ID = 1

CONSTITUTION_DOCUMENT_IDS = (
    3,
    4,
)

EXPECTED_CONSTITUTION_CHUNKS = 724
EXPECTED_EMBEDDING_DIMENSION = 768


def validate_bns_chunk_scope(
    chunks,
) -> None:
    """
    Safety check before embedding.

    Every supplied chunk must belong exclusively
    to the canonical BNS document/version.
    """

    for chunk in chunks:

        if (
            chunk.document_id
            != BNS_DOCUMENT_ID
        ):
            raise RuntimeError(
                "Non-BNS document chunk reached "
                "the BNS embedding pipeline."
            )

        if chunk.act_id != BNS_ACT_ID:
            raise RuntimeError(
                "Unexpected act_id reached "
                "the BNS embedding pipeline."
            )

        if (
            chunk.version_id
            != BNS_VERSION_ID
        ):
            raise RuntimeError(
                "Unexpected version_id reached "
                "the BNS embedding pipeline."
            )


async def assert_constitution_unchanged(
    db,
) -> None:

    result = await db.execute(
        select(
            func.count(
                LegalChunk.id
            ),
            func.count(
                LegalChunk.embedding
            ),
        )
        .where(
            LegalChunk.document_id.in_(
                CONSTITUTION_DOCUMENT_IDS
            )
        )
    )

    row = result.one()

    chunk_count = int(
        row[0]
    )

    embedded_count = int(
        row[1]
    )

    if (
        chunk_count
        != EXPECTED_CONSTITUTION_CHUNKS
        or embedded_count
        != EXPECTED_CONSTITUTION_CHUNKS
    ):
        raise RuntimeError(
            "Constitution safety invariant "
            "failed. Expected "
            f"{EXPECTED_CONSTITUTION_CHUNKS} "
            "chunks and embeddings, found "
            f"{chunk_count} chunks and "
            f"{embedded_count} embeddings."
        )


async def assert_bns_metadata_scope(
    db,
) -> None:
    """
    Ensure every chunk under document_id=2 also
    carries the expected BNS act/version IDs.

    NULL metadata is treated as invalid.
    """

    result = await db.execute(
        select(
            func.count(
                LegalChunk.id
            )
        )
        .where(
            LegalChunk.document_id
            == BNS_DOCUMENT_ID,
            or_(
                LegalChunk.act_id.is_(
                    None
                ),
                LegalChunk.act_id
                != BNS_ACT_ID,
                LegalChunk.version_id.is_(
                    None
                ),
                LegalChunk.version_id
                != BNS_VERSION_ID,
            ),
        )
    )

    invalid_count = (
        result.scalar_one()
    )

    if invalid_count:
        raise RuntimeError(
            "BNS chunk metadata safety "
            "check failed. Found "
            f"{invalid_count} chunk(s) "
            "with an unexpected act_id "
            "or version_id."
        )


async def embed_bns_chunks() -> None:

    provider = (
        get_embedding_provider()
    )

    async with AsyncSessionLocal() as db:

        # -----------------------------------------
        # Hard safety checks
        # -----------------------------------------

        await assert_constitution_unchanged(
            db
        )

        await assert_bns_metadata_scope(
            db
        )

        # -----------------------------------------
        # Ensure BNS chunks actually exist
        # -----------------------------------------

        count_result = await db.execute(
            select(
                func.count(
                    LegalChunk.id
                )
            )
            .where(
                LegalChunk.document_id
                == BNS_DOCUMENT_ID,
                LegalChunk.act_id
                == BNS_ACT_ID,
                LegalChunk.version_id
                == BNS_VERSION_ID,
            )
        )

        bns_chunk_count = (
            count_result.scalar_one()
        )

        if bns_chunk_count == 0:
            raise RuntimeError(
                "No BNS chunks found. "
                "Run BNS chunk creation first."
            )

        # -----------------------------------------
        # Select ONLY unembedded BNS chunks
        # -----------------------------------------

        result = await db.execute(
            select(
                LegalChunk
            )
            .where(
                LegalChunk.document_id
                == BNS_DOCUMENT_ID,
                LegalChunk.act_id
                == BNS_ACT_ID,
                LegalChunk.version_id
                == BNS_VERSION_ID,
                LegalChunk.embedding.is_(
                    None
                ),
            )
            .order_by(
                LegalChunk.id
            )
        )

        chunks = list(
            result.scalars().all()
        )

        validate_bns_chunk_scope(
            chunks
        )

        total = len(
            chunks
        )

        if total == 0:

            print(
                "No unembedded BNS "
                "legal chunks found."
            )

            await assert_constitution_unchanged(
                db
            )

            return

        print(
            f"BNS chunks in database: "
            f"{bns_chunk_count}"
        )

        print(
            f"Unembedded BNS chunks: "
            f"{total}"
        )

        print(
            f"Embedding batch size: "
            f"{BATCH_SIZE}"
        )

        print()

        processed = 0

        for start in range(
            0,
            total,
            BATCH_SIZE,
        ):

            batch = chunks[
                start:
                start + BATCH_SIZE
            ]

            validate_bns_chunk_scope(
                batch
            )

            texts = [
                chunk.content
                for chunk in batch
            ]

            print(
                f"Embedding BNS chunks "
                f"{start + 1}-"
                f"{start + len(batch)} "
                f"of {total}..."
            )

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
                    "Number of embeddings "
                    "does not match number "
                    "of BNS chunks."
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
                    != EXPECTED_EMBEDDING_DIMENSION
                ):
                    raise RuntimeError(
                        "Unexpected embedding "
                        "dimension for BNS "
                        f"chunk {chunk.id}: "
                        f"{len(embedding)}"
                    )

                chunk.embedding = (
                    embedding
                )

            await db.commit()

            processed += len(
                batch
            )

            print(
                f"Saved "
                f"{processed}/{total} "
                "BNS embeddings."
            )

            print()

        # -----------------------------------------
        # Final safety verification
        # -----------------------------------------

        await assert_constitution_unchanged(
            db
        )

        await assert_bns_metadata_scope(
            db
        )

        remaining_result = (
            await db.execute(
                select(
                    func.count(
                        LegalChunk.id
                    )
                )
                .where(
                    LegalChunk.document_id
                    == BNS_DOCUMENT_ID,
                    LegalChunk.act_id
                    == BNS_ACT_ID,
                    LegalChunk.version_id
                    == BNS_VERSION_ID,
                    LegalChunk.embedding.is_(
                        None
                    ),
                )
            )
        )

        remaining = (
            remaining_result.scalar_one()
        )

        if remaining != 0:
            raise RuntimeError(
                "BNS embedding pass "
                "finished with "
                f"{remaining} unembedded "
                "chunk(s)."
            )

        print(
            "================================"
        )

        print(
            "BNS embedding generation "
            "complete."
        )

        print(
            f"Total embedded this run: "
            f"{processed}"
        )

        print(
            "Constitution invariant: "
            "724 chunks / 724 embeddings"
        )

        print(
            "================================"
        )


if __name__ == "__main__":
    asyncio.run(
        embed_bns_chunks()
    )