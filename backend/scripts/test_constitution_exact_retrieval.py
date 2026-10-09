import asyncio

from app.db.session import AsyncSessionLocal
from app.services.legal_retrieval_orchestrator import (
    LegalRetrievalOrchestrator,
)


QUERIES = [
    "What does Article 21 say?",
    "What is Article 14?",
    "Explain Article 243-I",
    "What does Article 238 say?",
    "right to life and personal liberty",
    "freedom of speech",
]


async def main() -> None:
    orchestrator = (
        LegalRetrievalOrchestrator()
    )

    async with AsyncSessionLocal() as db:
        for query in QUERIES:
            print()
            print("=" * 70)
            print(query)
            print("=" * 70)

            result = await orchestrator.retrieve(
                db=db,
                query=query,
                top_k=5,
                candidate_k=20,
            )

            print(
                "Domain:",
                result.analysis.domain.value,
            )

            print(
                "Exact reference:",
                result.exact_reference,
            )

            print(
                "Exact status:",
                result.exact_reference_status,
            )

            print(
                "Legal jurisdiction:",
                result.legal_jurisdiction,
            )

            print(
                "Reason:",
                result.retrieval_reason,
            )

            print(
                "Chunks:",
                len(result.chunks),
            )

            for chunk in result.chunks:
                print(
                    "  ",
                    chunk.content[
                        :180
                    ].replace(
                        "\n",
                        " ",
                    ),
                )


if __name__ == "__main__":
    asyncio.run(main())