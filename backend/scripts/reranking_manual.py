import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk
from app.services.reranking import (
    get_reranker_provider,
)


async def test_reranking() -> None:

    query = "What is the punishment for theft?"

    print("=" * 80)
    print("NYAYAAI — SEMANTIC RERANKER TEST")
    print("=" * 80)

    print(f"\nQuery: {query}")

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(LegalChunk)
            .where(
                LegalChunk.embedding.is_not(None)
            )
            .order_by(LegalChunk.id)
            .limit(20)
        )

        chunks = list(
            result.scalars().all()
        )

        print(
            f"\nCandidate chunks: "
            f"{len(chunks)}"
        )

        reranker = get_reranker_provider()

        print(
            f"Reranker: "
            f"{type(reranker).__name__}"
        )

        reranked = await reranker.rerank(
            query=query,
            chunks=chunks,
            top_k=5,
        )

    print(
        f"\nRetrieved {len(reranked)} "
        f"reranked chunks:\n"
    )

    for rank, chunk in enumerate(
        reranked,
        start=1,
    ):

        print("-" * 80)

        print(f"Rank: {rank}")
        print(f"Chunk ID: {chunk.id}")
        print(
            f"Section ID: "
            f"{chunk.section_id}"
        )

        print("\nContent:")
        print(chunk.content)

        print()


if __name__ == "__main__":
    asyncio.run(
        test_reranking()
    )