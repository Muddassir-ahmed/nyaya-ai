from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.act import Act
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument
from app.models.section import Section
from app.services.hybrid_retrieval import (
    hybrid_search_legal_chunks,
)


TEST_QUERIES = [
    "What does Article 21 say?",
    "What is Article 14?",
    "Explain Article 243-I",
    "right to life and personal liberty",
    "equality before law",
    "freedom of speech",
    "constitutional remedies",
    "what does the Preamble say about secularism?",
    "what is in the Seventh Schedule?",
    "what does Article 238 say?",
]


TOP_K = 5
CANDIDATE_K = 20


async def describe_chunk(
    db,
    chunk: LegalChunk,
    rank: int,
) -> None:
    document = await db.get(
        LegalDocument,
        chunk.document_id,
    )

    act = None

    if chunk.act_id is not None:
        act = await db.get(
            Act,
            chunk.act_id,
        )

    section = None

    if chunk.section_id is not None:
        section = await db.get(
            Section,
            chunk.section_id,
        )

    print(
        f"\n  Rank {rank}"
    )

    print(
        f"  Chunk ID: "
        f"{chunk.id}"
    )

    print(
        f"  Document: "
        f"{document.title if document else None}"
    )

    print(
        f"  Act: "
        f"{act.name if act else None}"
    )

    if section is not None:
        print(
            f"  Provision: "
            f"{section.section_number}"
        )

        print(
            f"  Title: "
            f"{section.title}"
        )
    else:
        print(
            "  Provision: "
            "document-level chunk"
        )

    preview = (
        chunk.content
        .replace(
            "\n",
            " ",
        )
        .strip()
    )

    if len(preview) > 300:
        preview = (
            preview[:300]
            + "..."
        )

    print(
        f"  Preview: "
        f"{preview}"
    )


async def run_query(
    db,
    query: str,
) -> None:
    print()
    print(
        "=" * 80
    )

    print(
        f"QUERY: {query}"
    )

    print(
        "=" * 80
    )

    chunks = (
        await hybrid_search_legal_chunks(
            db=db,
            query=query,
            top_k=TOP_K,
            candidate_k=CANDIDATE_K,
            jurisdiction_id=None,
            effective_date=None,
        )
    )

    print(
        f"Results returned: "
        f"{len(chunks)}"
    )

    for rank, chunk in enumerate(
        chunks,
        start=1,
    ):
        await describe_chunk(
            db,
            chunk,
            rank,
        )


async def main() -> None:
    async with AsyncSessionLocal() as db:

        print(
            "================================"
        )

        print(
            "Constitution Hybrid Retrieval "
            "Baseline"
        )

        print(
            "================================"
        )

        for query in TEST_QUERIES:
            await run_query(
                db,
                query,
            )


if __name__ == "__main__":
    asyncio.run(main())