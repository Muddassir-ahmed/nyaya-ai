import asyncio

from app.db.session import AsyncSessionLocal
from app.services.query_orchestrator import (
    QueryOrchestrator,
)


TESTS = [
    "What does Article 238 say?",
    "What does Article 999 say?",
]


async def main() -> None:
    orchestrator = QueryOrchestrator()

    async with AsyncSessionLocal() as db:

        for query in TESTS:
            print()
            print("=" * 70)
            print(query)
            print("=" * 70)

            result = await orchestrator.handle(
                db=db,
                query=query,
            )

            print(
                "Route:",
                result.route,
            )

            print(
                "Domain:",
                result.analysis.domain.value,
            )

            print(
                "Retrieval performed:",
                result.retrieval_performed,
            )

            print(
                "Routing reason:",
                result.routing_reason,
            )

            print(
                "Answer blocked:",
                result.answer_blocked,
            )

            print(
                "Evidence count:",
                len(result.evidence),
            )

            if result.legal_answer:
                print(
                    "Summary:",
                    result.legal_answer.summary,
                )

                print(
                    "Caveats:",
                    result.legal_answer.caveats,
                )


if __name__ == "__main__":
    asyncio.run(main())