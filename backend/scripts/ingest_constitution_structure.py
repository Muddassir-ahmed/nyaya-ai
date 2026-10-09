from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.legal_document import LegalDocument
from app.models.legal_version import LegalVersion
from app.models.section import Section


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PARSED_FILE = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
    / "constitution_parsed.json"
)


DOCUMENT_TITLE = (
    "The Constitution of India"
)

VERSION_LABEL = (
    "Constitution of India — "
    "As on 1 May 2026"
)

EXPECTED_SHA256 = (
    "4C8E93689EC245E26DB08E22B5FF3AD"
    "645C98736F0E5B7C8B6638ACD7861F85B"
)

EXPECTED_ARTICLE_COUNT = 506
EXPECTED_OMITTED_COUNT = 34
EXPECTED_SCHEDULE_COUNT = 12


def load_and_validate_parsed_data() -> dict[str, Any]:
    if not PARSED_FILE.exists():
        raise FileNotFoundError(
            "Parsed Constitution JSON "
            f"not found: {PARSED_FILE}"
        )

    data = json.loads(
        PARSED_FILE.read_text(
            encoding="utf-8"
        )
    )

    metadata = data.get(
        "metadata",
        {},
    )

    articles = data.get(
        "articles",
        [],
    )

    schedules = data.get(
        "schedules",
        [],
    )

    # -------------------------------------------------
    # Source integrity
    # -------------------------------------------------

    source_hash = metadata.get(
        "source_pdf_sha256"
    )

    if source_hash != EXPECTED_SHA256:
        raise RuntimeError(
            "Parsed JSON source hash does "
            "not match the locked "
            "Constitution source.\n"
            f"Expected: {EXPECTED_SHA256}\n"
            f"Found:    {source_hash}"
        )

    # -------------------------------------------------
    # Article count
    # -------------------------------------------------

    if (
        len(articles)
        != EXPECTED_ARTICLE_COUNT
    ):
        raise RuntimeError(
            "Unexpected Constitution "
            "Article count.\n"
            f"Expected: "
            f"{EXPECTED_ARTICLE_COUNT}\n"
            f"Found:    {len(articles)}"
        )

    # -------------------------------------------------
    # Schedule count
    # -------------------------------------------------

    if (
        len(schedules)
        != EXPECTED_SCHEDULE_COUNT
    ):
        raise RuntimeError(
            "Unexpected Constitution "
            "Schedule count.\n"
            f"Expected: "
            f"{EXPECTED_SCHEDULE_COUNT}\n"
            f"Found:    {len(schedules)}"
        )

    # -------------------------------------------------
    # Article ID uniqueness
    # -------------------------------------------------

    article_numbers = [
        str(
            article[
                "article_number"
            ]
        ).strip()
        for article in articles
    ]

    if len(
        set(article_numbers)
    ) != len(article_numbers):
        raise RuntimeError(
            "Duplicate Article identifiers "
            "found in parsed Constitution."
        )

    if (
        article_numbers[0] != "1"
        or article_numbers[-1] != "395"
    ):
        raise RuntimeError(
            "Constitution Article boundaries "
            "are invalid. Expected Article 1 "
            "through Article 395."
        )

    # -------------------------------------------------
    # Omitted provisions
    # -------------------------------------------------

    omitted_count = sum(
        1
        for article in articles
        if article.get(
            "is_omitted",
            False,
        )
    )

    if (
        omitted_count
        != EXPECTED_OMITTED_COUNT
    ):
        raise RuntimeError(
            "Unexpected omitted Article "
            "count.\n"
            f"Expected: "
            f"{EXPECTED_OMITTED_COUNT}\n"
            f"Found:    {omitted_count}"
        )

    # -------------------------------------------------
    # Known critical Articles
    # -------------------------------------------------

    required = {
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
    }

    missing = (
        required
        - set(article_numbers)
    )

    if missing:
        raise RuntimeError(
            "Required Articles missing: "
            + ", ".join(
                sorted(missing)
            )
        )

    article_map = {
        article[
            "article_number"
        ]:
        article
        for article in articles
    }

    if article_map[
        "237"
    ].get(
        "is_omitted",
        False,
    ):
        raise RuntimeError(
            "Article 237 is incorrectly "
            "marked as omitted."
        )

    if not article_map[
        "238"
    ].get(
        "is_omitted",
        False,
    ):
        raise RuntimeError(
            "Article 238 should be "
            "marked as omitted."
        )

    if article_map[
        "239"
    ].get(
        "is_omitted",
        False,
    ):
        raise RuntimeError(
            "Article 239 is incorrectly "
            "marked as omitted."
        )

    print(
        "Parsed Constitution validation "
        "passed."
    )

    print(
        f"Articles: {len(articles)}"
    )

    print(
        f"Omitted Articles: "
        f"{omitted_count}"
    )

    print(
        f"Schedules retained in JSON: "
        f"{len(schedules)}"
    )

    return data


async def get_primary_document(
    db: AsyncSession,
) -> LegalDocument:
    result = await db.execute(
        select(LegalDocument)
        .where(
            LegalDocument.title
            == DOCUMENT_TITLE,

            LegalDocument.document_type
            == "constitution",
        )
    )

    documents = (
        result.scalars().all()
    )

    if len(documents) != 1:
        raise RuntimeError(
            "Expected exactly one canonical "
            "Constitution LegalDocument, "
            f"found {len(documents)}."
        )

    document = documents[0]

    if not document.is_verified:
        raise RuntimeError(
            "Canonical Constitution "
            "document is not verified."
        )

    if (
        document.file_hash
        != EXPECTED_SHA256
    ):
        raise RuntimeError(
            "Canonical Constitution "
            "LegalDocument hash does not "
            "match the locked source."
        )

    if document.act_id is None:
        raise RuntimeError(
            "Constitution LegalDocument "
            "has no act_id."
        )

    return document


async def get_constitution_version(
    db: AsyncSession,
    *,
    act_id: int,
) -> LegalVersion:
    result = await db.execute(
        select(LegalVersion)
        .where(
            LegalVersion.act_id
            == act_id,

            LegalVersion.version_label
            == VERSION_LABEL,
        )
    )

    versions = (
        result.scalars().all()
    )

    if len(versions) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "Constitution version "
            f"'{VERSION_LABEL}', "
            f"found {len(versions)}."
        )

    version = versions[0]

    if version.status != "active":
        raise RuntimeError(
            "Constitution version "
            "is not active."
        )

    return version


def article_to_section_text(
    article: dict[str, Any],
) -> str:
    """
    Convert a parsed Constitution Article
    into Section.text.

    Active provisions store their parsed
    constitutional body text.

    Omitted provisions are retained as
    structural Article records, but do not
    invent substantive legal text.
    """

    if article.get(
        "is_omitted",
        False,
    ):
        return "[Omitted.]"

    text = str(
        article.get(
            "text",
            "",
        )
    ).strip()

    if not text:
        raise RuntimeError(
            "Active Article has empty "
            "body text: "
            f"{article['article_number']}"
        )

    return text


async def ingest_constitution_structure() -> None:
    data = (
        load_and_validate_parsed_data()
    )

    articles: list[
        dict[str, Any]
    ] = data["articles"]

    async with AsyncSessionLocal() as db:
        try:
            document = (
                await get_primary_document(
                    db
                )
            )

            version = (
                await
                get_constitution_version(
                    db,
                    act_id=(
                        document.act_id
                    ),
                )
            )

            # -----------------------------------------
            # Load all existing Constitution Articles
            # for this exact version.
            # -----------------------------------------

            existing_result = (
                await db.execute(
                    select(Section)
                    .where(
                        Section.version_id
                        == version.id
                    )
                )
            )

            existing_sections = (
                existing_result
                .scalars()
                .all()
            )

            existing_map = {
                section.section_number:
                    section
                for section
                in existing_sections
            }

            expected_numbers = {
                str(
                    article[
                        "article_number"
                    ]
                ).strip()
                for article
                in articles
            }

            existing_numbers = set(
                existing_map
            )

            # -----------------------------------------
            # Safety:
            #
            # Do not silently delete unexpected
            # records from a legal version.
            # -----------------------------------------

            unexpected = (
                existing_numbers
                - expected_numbers
            )

            if unexpected:
                raise RuntimeError(
                    "Unexpected Section records "
                    "already exist for the "
                    "Constitution version:\n"
                    + ", ".join(
                        sorted(
                            unexpected
                        )
                    )
                    + "\nRefusing to delete them "
                    "automatically."
                )

            created = 0
            updated = 0
            unchanged = 0

            omitted = 0

            print(
                "\nIngesting Constitution "
                "Articles..."
            )

            for article in articles:
                number = str(
                    article[
                        "article_number"
                    ]
                ).strip()

                title = str(
                    article.get(
                        "title",
                        "",
                    )
                    or ""
                ).strip()

                title_value = (
                    title
                    if title
                    else None
                )

                text = (
                    article_to_section_text(
                        article
                    )
                )

                if article.get(
                    "is_omitted",
                    False,
                ):
                    omitted += 1

                existing = (
                    existing_map.get(
                        number
                    )
                )

                if existing is None:
                    section = Section(
                        version_id=(
                            version.id
                        ),
                        section_number=(
                            number
                        ),
                        title=title_value,
                        text=text,
                    )

                    db.add(section)

                    created += 1

                    continue

                changed = False

                if (
                    existing.title
                    != title_value
                ):
                    existing.title = (
                        title_value
                    )

                    changed = True

                if (
                    existing.text
                    != text
                ):
                    existing.text = text

                    changed = True

                if changed:
                    updated += 1
                else:
                    unchanged += 1

            await db.flush()

            # -----------------------------------------
            # Verify DB count before commit.
            # -----------------------------------------

            count_result = await db.execute(
                select(Section)
                .where(
                    Section.version_id
                    == version.id
                )
            )

            final_sections = (
                count_result
                .scalars()
                .all()
            )

            if (
                len(final_sections)
                != EXPECTED_ARTICLE_COUNT
            ):
                raise RuntimeError(
                    "Constitution Section "
                    "count verification failed "
                    "before commit.\n"
                    f"Expected: "
                    f"{EXPECTED_ARTICLE_COUNT}\n"
                    f"Found: "
                    f"{len(final_sections)}"
                )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    print(
        "\n================================"
    )

    print(
        "Constitution structure "
        "ingestion complete."
    )

    print(
        "================================"
    )

    print(
        f"Document ID: {document.id}"
    )

    print(
        f"Act ID: {document.act_id}"
    )

    print(
        f"Version ID: {version.id}"
    )

    print(
        f"Articles total: "
        f"{EXPECTED_ARTICLE_COUNT}"
    )

    print(
        f"Created: {created}"
    )

    print(
        f"Updated: {updated}"
    )

    print(
        f"Unchanged: {unchanged}"
    )

    print(
        f"Omitted Articles: {omitted}"
    )

    print(
        "Schedules ingested as Sections: 0"
    )

    print(
        "Schedules remain preserved in "
        "constitution_parsed.json."
    )


if __name__ == "__main__":
    asyncio.run(
        ingest_constitution_structure()
    )