import asyncio

from app.db.session import AsyncSessionLocal
from app.services.hybrid_retrieval import (
    hybrid_search_legal_chunks,
)


async def test_hybrid_retrieval() -> None:

    query = "What is the punishment for theft?"

    print("=" * 80)
    print("NYAYAAI — HYBRID + SEMANTIC RERANKING TEST")
    print("=" * 80)

    print(f"\nQuery: {query}")

    async with AsyncSessionLocal() as db:

        chunks = await hybrid_search_legal_chunks(
            db=db,
            query=query,
            top_k=5,
            candidate_k=20,
        )

    if not chunks:
        print(
            "\nNo legal chunks found."
        )
        return

    print(
        f"\nFinal retrieved chunks: "
        f"{len(chunks)}\n"
    )

    for rank, chunk in enumerate(
        chunks,
        start=1,
    ):

        print("-" * 80)

        print(f"Final Rank: {rank}")
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
        test_hybrid_retrieval()
    )