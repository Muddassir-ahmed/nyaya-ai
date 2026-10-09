import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument
from app.models.section import Section


async def main() -> None:
    async with AsyncSessionLocal() as db:
        document_result = await db.execute(
            select(LegalDocument)
            .where(
                LegalDocument.title
                == "The Constitution of India",

                LegalDocument.document_type
                == "constitution",
            )
        )

        document = (
            document_result
            .scalar_one()
        )

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
            result.scalars().all()
        )

        print(
            "================================"
        )
        print(
            "Constitution chunk verification"
        )
        print(
            "================================"
        )

        print(
            f"Total chunks: "
            f"{len(chunks)}"
        )

        if not chunks:
            raise RuntimeError(
                "No Constitution chunks found."
            )

        embedded = sum(
            1
            for chunk in chunks
            if chunk.embedding
            is not None
        )

        print(
            f"Already embedded: "
            f"{embedded}"
        )

        article_chunks = [
            chunk
            for chunk in chunks
            if chunk.section_id
            is not None
        ]

        document_chunks = [
            chunk
            for chunk in chunks
            if chunk.section_id
            is None
        ]

        print(
            f"Article-linked chunks: "
            f"{len(article_chunks)}"
        )

        print(
            f"Preamble/Schedule chunks: "
            f"{len(document_chunks)}"
        )

        # -------------------------------
        # Cache Section objects for lookups
        # -------------------------------

        section_cache = {}

        for chunk in article_chunks:
            if (
                chunk.section_id
                not in section_cache
            ):
                section_cache[
                    chunk.section_id
                ] = await db.get(
                    Section,
                    chunk.section_id,
                )

        # -------------------------------
        # Verify specific Article chunks
        # -------------------------------

        for number in [
            "14",
            "21",
            "21A",
            "32",
            "226",
            "243-I",
            "368",
            "370",
            "395",
        ]:
            matching = [
                chunk
                for chunk
                in article_chunks
                if (
                    section_cache.get(
                        chunk.section_id
                    )
                    is not None
                    and
                    section_cache[
                        chunk.section_id
                    ].section_number
                    == number
                )
            ]

            if not matching:
                raise RuntimeError(
                    f"No chunks for "
                    f"Article {number}."
                )

            print(
                f"\nArticle {number}"
            )

            print(
                f"Chunks: "
                f"{len(matching)}"
            )

            print(
                "Preview:"
            )

            print(
                matching[0]
                .content[:350]
            )

        # -------------------------------
        # Verify omitted Article 238
        # has NO retrieval chunks.
        # -------------------------------

        omitted_section_result = (
            await db.execute(
                select(Section)
                .where(
                    Section.section_number
                    == "238"
                )
            )
        )

        omitted_candidates = (
            omitted_section_result
            .scalars()
            .all()
        )

        constitution_238 = [
            section
            for section
            in omitted_candidates
            if section.text
            == "[Omitted.]"
        ]

        if len(
            constitution_238
        ) != 1:
            raise RuntimeError(
                "Could not uniquely identify "
                "Constitution Article 238."
            )

        article_238 = (
            constitution_238[0]
        )

        bad_chunks = [
            chunk
            for chunk in chunks
            if chunk.section_id
            == article_238.id
        ]

        if bad_chunks:
            raise RuntimeError(
                "Omitted Article 238 "
                "has retrieval chunks."
            )

        print(
            "\nArticle 238 chunks: 0 ✅"
        )

        # -------------------------------
        # Preamble presence
        # -------------------------------

        if not any(
            "Preamble"
            in chunk.content
            and
            "WE, THE PEOPLE OF INDIA"
            in chunk.content
            for chunk in document_chunks
        ):
            raise RuntimeError(
                "Preamble chunk not found."
            )

        print(
            "Preamble chunk found ✅"
        )

        # -------------------------------
        # Schedule presence
        # -------------------------------

        schedule_names = [
            "First",
            "Second",
            "Third",
            "Fourth",
            "Fifth",
            "Sixth",
            "Seventh",
            "Eighth",
            "Ninth",
            "Tenth",
            "Eleventh",
            "Twelfth",
        ]

        for name in schedule_names:
            expected = (
                f"{name} Schedule"
            )

            if not any(
                expected
                in chunk.content
                for chunk
                in document_chunks
            ):
                raise RuntimeError(
                    "Missing Schedule "
                    f"chunk: {expected}"
                )

        print(
            "All 12 Schedule "
            "families found ✅"
        )

        print(
            "\nVALIDATION PASSED ✅"
        )


if __name__ == "__main__":
    asyncio.run(main())