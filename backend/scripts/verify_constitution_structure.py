import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.act import Act
from app.models.legal_version import LegalVersion
from app.models.section import Section


VERSION_LABEL = (
    "Constitution of India — "
    "As on 1 May 2026"
)


SAMPLE_ARTICLES = [
    "1",
    "14",
    "19",
    "21",
    "21A",
    "32",
    "51A",
    "226",
    "237",
    "238",
    "239",
    "239AA",
    "243-I",
    "243Z-I",
    "368",
    "370",
    "371-I",
    "394A",
    "395",
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        act_result = await db.execute(
            select(Act)
            .where(
                Act.name
                == "The Constitution of India"
            )
        )

        act = (
            act_result.scalar_one()
        )

        version_result = await db.execute(
            select(LegalVersion)
            .where(
                LegalVersion.act_id
                == act.id,

                LegalVersion.version_label
                == VERSION_LABEL,
            )
        )

        version = (
            version_result.scalar_one()
        )

        sections_result = await db.execute(
            select(Section)
            .where(
                Section.version_id
                == version.id
            )
        )

        sections = (
            sections_result
            .scalars()
            .all()
        )

        section_map = {
            section.section_number:
                section
            for section
            in sections
        }

        omitted = [
            section
            for section
            in sections
            if section.text
            == "[Omitted.]"
        ]

        print(
            "================================"
        )

        print(
            "Constitution DB verification"
        )

        print(
            "================================"
        )

        print(
            f"Act ID: {act.id}"
        )

        print(
            f"Version ID: {version.id}"
        )

        print(
            f"Article records: "
            f"{len(sections)}"
        )

        print(
            f"Omitted records: "
            f"{len(omitted)}"
        )

        if len(sections) != 506:
            raise RuntimeError(
                "Expected 506 Article "
                "records."
            )

        if len(omitted) != 34:
            raise RuntimeError(
                "Expected 34 omitted "
                "Article records."
            )

        print(
            "\nSample Articles:"
        )

        for number in SAMPLE_ARTICLES:
            section = (
                section_map.get(
                    number
                )
            )

            if section is None:
                raise RuntimeError(
                    f"Article {number} "
                    "not found."
                )

            preview = (
                section.text[
                    :120
                ]
                .replace(
                    "\n",
                    " ",
                )
            )

            print(
                f"\nArticle {number}"
            )

            print(
                f"Title: "
                f"{section.title}"
            )

            print(
                f"Text: {preview}"
            )

        if (
            section_map[
                "237"
            ].text
            == "[Omitted.]"
        ):
            raise RuntimeError(
                "Article 237 should "
                "not be omitted."
            )

        if (
            section_map[
                "238"
            ].text
            != "[Omitted.]"
        ):
            raise RuntimeError(
                "Article 238 should "
                "be omitted."
            )

        if (
            section_map[
                "239"
            ].text
            == "[Omitted.]"
        ):
            raise RuntimeError(
                "Article 239 should "
                "not be omitted."
            )

        print(
            "\nVALIDATION PASSED ✅"
        )


if __name__ == "__main__":
    asyncio.run(main())