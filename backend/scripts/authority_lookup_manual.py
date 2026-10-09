import asyncio

from app.db.session import AsyncSessionLocal
from app.services.authority_orchestrator import (
    AuthorityOrchestrator,
)


async def main():
    async with AsyncSessionLocal() as session:
        orchestrator = AuthorityOrchestrator()

        response = await orchestrator.handle(
            db=session,
            query=(
                "Where should I report my stolen bike "
                "in Assam?"
            ),
        )

        print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())