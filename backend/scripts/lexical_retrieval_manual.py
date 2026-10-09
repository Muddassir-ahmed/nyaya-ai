import asyncio

from app.db.session import AsyncSessionLocal
from app.services.lexical_retrieval import (
    search_legal_chunks_lexical,
)


async def test_lexical_retrieval() -> None:
    query = "What is the punishment for theft?"

    print("=" * 60)
    print("NYAYAAI LEXICAL RETRIEVAL TEST")
    print("=" * 60)
    print(f"\nQuery: {query}\n")

    async with AsyncSessionLocal() as db:
        chunks = await search_legal_chunks_lexical(
            db=db,
            query=query,
            top_k=5,
        )

    if not chunks:
        print("No legal chunks found.")
        return

    print(f"Retrieved {len(chunks)} chunks:\n")

    for rank, chunk in enumerate(chunks, start=1):
        print("-" * 60)
        print(f"Rank: {rank}")
        print(f"Chunk ID: {chunk.id}")
        print(f"Section ID: {chunk.section_id}")
        print(f"Subsection ID: {chunk.subsection_id}")
        print(f"Clause ID: {chunk.clause_id}")

        print("\nContent:")
        print(chunk.content)

        print()


if __name__ == "__main__":
    asyncio.run(test_lexical_retrieval())