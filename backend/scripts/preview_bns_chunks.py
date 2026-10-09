import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk


BNS_DOCUMENT_ID = 2
BNS_ACT_ID = 1
BNS_VERSION_ID = 1


async def preview_chunks() -> None:

    async with AsyncSessionLocal() as db:

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
            )
            .order_by(
                LegalChunk.id
            )
            .limit(
                10
            )
        )

        chunks = list(
            result.scalars().all()
        )

        print(
            "=" * 70
        )

        print(
            f"Showing "
            f"{len(chunks)} "
            "BNS chunks"
        )

        print(
            "=" * 70
        )

        for chunk in chunks:

            print(
                "\n"
                + "-" * 70
            )

            print(
                f"Chunk ID       : "
                f"{chunk.id}\n"
                f"Document ID    : "
                f"{chunk.document_id}\n"
                f"Act ID         : "
                f"{chunk.act_id}\n"
                f"Version ID     : "
                f"{chunk.version_id}\n"
                f"Chunk Index    : "
                f"{chunk.chunk_index}\n"
                f"Section ID     : "
                f"{chunk.section_id}\n"
                f"Subsection ID  : "
                f"{chunk.subsection_id}\n"
                f"Clause ID      : "
                f"{chunk.clause_id}"
            )

            print(
                "\nContent:"
            )

            print(
                chunk.content[:700]
            )

        print(
            "\n"
            + "=" * 70
        )


if __name__ == "__main__":
    asyncio.run(
        preview_chunks()
    )