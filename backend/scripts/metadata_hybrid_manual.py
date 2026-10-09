import asyncio

from app.db.session import AsyncSessionLocal
from app.services.hybrid_retrieval import (
    hybrid_search_legal_chunks,
)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        results = await hybrid_search_legal_chunks(
            db=db,
            query="What is the punishment for theft?",
            top_k=5,
            candidate_k=20,
            act_id=1,
            jurisdiction_id=1,
        )

        print()
        print("================================")
        print("Metadata-Aware Hybrid Retrieval")
        print("================================")
        print(f"Results: {len(results)}")
        print()

        for rank, chunk in enumerate(results, start=1):
            print(f"--- Result {rank} ---")
            print(f"Chunk ID: {chunk.id}")
            print(f"Act ID: {chunk.act_id}")
            print(f"Version ID: {chunk.version_id}")
            print(f"Section ID: {chunk.section_id}")
            print(f"Content: {chunk.content[:300]}")
            print()


if __name__ == "__main__":
    asyncio.run(main())