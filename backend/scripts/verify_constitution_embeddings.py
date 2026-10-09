import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument


DOCUMENT_TITLE = "The Constitution of India"
DOCUMENT_TYPE = "constitution"

EXPECTED_CHUNKS = 724
EXPECTED_DIMENSION = 768

EXPECTED_SHA256 = (
    "4C8E93689EC245E26DB08E22B5FF3AD"
    "645C98736F0E5B7C8B6638ACD7861F85B"
)


async def main() -> None:
    async with AsyncSessionLocal() as db:

        # ---------------------------------
        # Canonical Constitution document
        # ---------------------------------

        document_result = await db.execute(
            select(LegalDocument)
            .where(
                LegalDocument.title
                == DOCUMENT_TITLE,

                LegalDocument.document_type
                == DOCUMENT_TYPE,
            )
        )

        documents = (
            document_result
            .scalars()
            .all()
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
                "Constitution document "
                "is not verified."
            )

        if (
            document.file_hash
            != EXPECTED_SHA256
        ):
            raise RuntimeError(
                "Constitution document hash "
                "does not match locked source."
            )

        # ---------------------------------
        # Load Constitution chunks ONLY
        # ---------------------------------

        result = await db.execute(
            select(LegalChunk)
            .where(
                LegalChunk.document_id
                == document.id
            )
            .order_by(
                LegalChunk.id
            )
        )

        chunks = (
            result.scalars()
            .all()
        )

        print(
            "================================"
        )
        print(
            "Constitution embedding verification"
        )
        print(
            "================================"
        )

        print(
            f"Document ID: {document.id}"
        )

        print(
            f"Chunks: {len(chunks)}"
        )

        if (
            len(chunks)
            != EXPECTED_CHUNKS
        ):
            raise RuntimeError(
                "Unexpected Constitution "
                "chunk count.\n"
                f"Expected: {EXPECTED_CHUNKS}\n"
                f"Found:    {len(chunks)}"
            )

        # ---------------------------------
        # Missing embeddings
        # ---------------------------------

        missing = [
            chunk
            for chunk in chunks
            if chunk.embedding is None
        ]

        embedded_count = (
            len(chunks)
            - len(missing)
        )

        print(
            f"Embedded: {embedded_count}"
        )

        print(
            f"Missing embeddings: "
            f"{len(missing)}"
        )

        if missing:
            raise RuntimeError(
                f"{len(missing)} Constitution "
                "chunks have no embedding."
            )

        # ---------------------------------
        # Vector dimension
        # ---------------------------------

        wrong_dimensions = []

        for chunk in chunks:
            dimension = len(
                chunk.embedding
            )

            if (
                dimension
                != EXPECTED_DIMENSION
            ):
                wrong_dimensions.append(
                    (
                        chunk.id,
                        dimension,
                    )
                )

        if wrong_dimensions:
            raise RuntimeError(
                "Invalid embedding dimensions "
                "detected:\n"
                f"{wrong_dimensions[:10]}"
            )

        print(
            f"Embedding dimension: "
            f"{EXPECTED_DIMENSION}"
        )

        # ---------------------------------
        # Content hashes
        # ---------------------------------

        missing_hashes = [
            chunk.id
            for chunk in chunks
            if not chunk.content_hash
        ]

        if missing_hashes:
            raise RuntimeError(
                "Chunks missing content_hash: "
                f"{missing_hashes[:10]}"
            )

        hashes = [
            chunk.content_hash
            for chunk in chunks
        ]

        unique_hashes = set(
            hashes
        )

        print(
            f"Unique content hashes: "
            f"{len(unique_hashes)}"
        )

        if (
            len(unique_hashes)
            != len(chunks)
        ):
            raise RuntimeError(
                "Duplicate Constitution "
                "content hashes detected."
            )

        # ---------------------------------
        # FTS generated column
        # ---------------------------------

        missing_search_vectors = [
            chunk.id
            for chunk in chunks
            if chunk.search_vector is None
        ]

        print(
            "FTS search vectors present: "
            f"{len(chunks) - len(missing_search_vectors)}"
        )

        if missing_search_vectors:
            raise RuntimeError(
                "Some Constitution chunks "
                "have no PostgreSQL "
                "search_vector."
            )

        print()
        print(
            "All Constitution chunks have "
            "valid 768d embeddings ✅"
        )

        print(
            "All Constitution chunks have "
            "FTS search vectors ✅"
        )

        print()
        print(
            "VALIDATION PASSED ✅"
        )


if __name__ == "__main__":
    asyncio.run(main())
