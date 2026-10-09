from __future__ import annotations

import asyncio
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk
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

EXPECTED_ARTICLES = 506
EXPECTED_OMITTED = 34
EXPECTED_ACTIVE = (
    EXPECTED_ARTICLES
    - EXPECTED_OMITTED
)

EXPECTED_SCHEDULES = 12

MAX_CHARS = 1800


def make_hash(
    content: str,
) -> str:
    return sha256(
        content.encode("utf-8")
    ).hexdigest()


def normalize_retrieval_text(
    text: str,
) -> str:
    """
    Conservative normalization for retrieval.

    IMPORTANT:
    This does NOT modify Section.text in the DB.

    We intentionally avoid speculative legal-text
    corrections such as changing:

        Pres ident
        exceptaccording
        co -operative

    because those may require source-specific
    correction rules.

    This function only normalizes whitespace and
    obvious extraction formatting noise.
    """

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def split_text(
    text: str,
    max_chars: int = MAX_CHARS,
) -> list[str]:
    """
    Split retrieval text without exceeding
    max_chars.

    Prefer paragraph boundaries first, then
    sentence-like boundaries, then words.
    """

    text = (
        normalize_retrieval_text(
            text
        )
    )

    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    paragraphs = [
        paragraph.strip()
        for paragraph
        in re.split(
            r"\n\s*\n",
            text,
        )
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current

        if current.strip():
            chunks.append(
                current.strip()
            )

        current = ""

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:

            candidate = (
                paragraph
                if not current
                else (
                    current
                    + "\n\n"
                    + paragraph
                )
            )

            if len(candidate) <= max_chars:
                current = candidate
                continue

            flush_current()
            current = paragraph
            continue

        # Paragraph itself is too large.
        flush_current()

        sentences = re.split(
            r"(?<=[.;:!?])\s+",
            paragraph,
        )

        sentence_buffer = ""

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            if len(sentence) <= max_chars:

                candidate = (
                    sentence
                    if not sentence_buffer
                    else (
                        sentence_buffer
                        + " "
                        + sentence
                    )
                )

                if (
                    len(candidate)
                    <= max_chars
                ):
                    sentence_buffer = (
                        candidate
                    )
                    continue

                if sentence_buffer:
                    chunks.append(
                        sentence_buffer
                    )

                sentence_buffer = (
                    sentence
                )

                continue

            # Single sentence is still too
            # large: final fallback = words.
            if sentence_buffer:
                chunks.append(
                    sentence_buffer
                )

                sentence_buffer = ""

            words = sentence.split()

            word_buffer = ""

            for word in words:
                candidate = (
                    word
                    if not word_buffer
                    else (
                        word_buffer
                        + " "
                        + word
                    )
                )

                if (
                    len(candidate)
                    <= max_chars
                ):
                    word_buffer = (
                        candidate
                    )
                    continue

                if word_buffer:
                    chunks.append(
                        word_buffer
                    )

                word_buffer = word

            if word_buffer:
                chunks.append(
                    word_buffer
                )

        if sentence_buffer:
            chunks.append(
                sentence_buffer
            )

    flush_current()

    return chunks


def add_contextual_chunks(
    chunks: list[dict[str, Any]],
    *,
    document_id: int,
    act_id: int,
    version_id: int,
    section_id: int | None,
    header: str,
    body: str,
) -> int:
    """
    Split the body while repeating the legal
    context header on EVERY resulting chunk.

    Example:

        The Constitution of India
        Part III — FUNDAMENTAL RIGHTS
        Article 19 — Protection of ...

        <fragment>

    This prevents continuation chunks from
    losing their Article / Schedule identity.
    """

    header = normalize_retrieval_text(
        header
    )

    body = normalize_retrieval_text(
        body
    )

    if not header:
        raise RuntimeError(
            "Chunk header cannot be empty."
        )

    if not body:
        return 0

    separator = "\n\n"

    body_budget = (
        MAX_CHARS
        - len(header)
        - len(separator)
    )

    if body_budget < 300:
        raise RuntimeError(
            "Chunk header is too large "
            "for the configured MAX_CHARS."
        )

    body_fragments = split_text(
        body,
        max_chars=body_budget,
    )

    for index, fragment in enumerate(
        body_fragments
    ):
        chunk_content = (
            f"{header}"
            f"{separator}"
            f"{fragment}"
        ).strip()

        if len(chunk_content) > MAX_CHARS:
            raise RuntimeError(
                "Generated chunk exceeds "
                f"MAX_CHARS={MAX_CHARS}. "
                f"Length={len(chunk_content)}"
            )

        chunks.append(
            {
                "document_id":
                    document_id,

                "act_id":
                    act_id,

                "version_id":
                    version_id,

                "section_id":
                    section_id,

                "subsection_id":
                    None,

                "clause_id":
                    None,

                "chunk_index":
                    index,

                "content":
                    chunk_content,

                "token_count":
                    None,

                "content_hash":
                    make_hash(
                        chunk_content
                    ),
            }
        )

    return len(body_fragments)


def load_parsed_constitution(
) -> dict[str, Any]:
    if not PARSED_FILE.exists():
        raise FileNotFoundError(
            "Constitution parsed JSON "
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

    preamble = str(
        data.get(
            "preamble",
            "",
        )
    ).strip()

    if (
        metadata.get(
            "source_pdf_sha256"
        )
        != EXPECTED_SHA256
    ):
        raise RuntimeError(
            "Parsed Constitution JSON "
            "does not match the locked "
            "canonical source."
        )

    if (
        len(articles)
        != EXPECTED_ARTICLES
    ):
        raise RuntimeError(
            "Expected "
            f"{EXPECTED_ARTICLES} "
            "Article records, found "
            f"{len(articles)}."
        )

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
        != EXPECTED_OMITTED
    ):
        raise RuntimeError(
            "Expected "
            f"{EXPECTED_OMITTED} "
            "omitted Articles, found "
            f"{omitted_count}."
        )

    if (
        len(schedules)
        != EXPECTED_SCHEDULES
    ):
        raise RuntimeError(
            "Expected 12 Schedules, "
            f"found {len(schedules)}."
        )

    if (
        "WE, THE PEOPLE OF INDIA"
        not in preamble
    ):
        raise RuntimeError(
            "Preamble validation failed."
        )

    return data


async def get_constitution_context(
    db: AsyncSession,
) -> tuple[
    LegalDocument,
    LegalVersion,
]:
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
            "Expected exactly one "
            "canonical Constitution "
            "document, found "
            f"{len(documents)}."
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
            "Constitution document hash "
            "does not match locked source."
        )

    if document.act_id is None:
        raise RuntimeError(
            "Constitution document "
            "has no act_id."
        )

    version_result = await db.execute(
        select(LegalVersion)
        .where(
            LegalVersion.act_id
            == document.act_id,

            LegalVersion.version_label
            == VERSION_LABEL,
        )
    )

    versions = (
        version_result
        .scalars()
        .all()
    )

    if len(versions) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "Constitution version, "
            f"found {len(versions)}."
        )

    version = versions[0]

    return (
        document,
        version,
    )


def build_article_header(
    article: dict[str, Any],
    section: Section,
) -> str:
    number = str(
        article[
            "article_number"
        ]
    ).strip()

    part_number = article.get(
        "part"
    )

    part_title = str(
        article.get(
            "part_title",
            "",
        )
        or ""
    ).strip()

    title = (
        section.title
        or ""
    ).strip()

    lines = [
        "The Constitution of India",
    ]

    if part_number:
        part_line = (
            f"Part {part_number}"
        )

        if part_title:
            part_line += (
                f" — {part_title}"
            )

        lines.append(
            part_line
        )

    article_line = (
        f"Article {number}"
    )

    if title:
        article_line += (
            f" — {title}"
        )

    lines.append(
        article_line
    )

    return "\n".join(
        lines
    )


def build_article_body(
    section: Section,
) -> str:
    return section.text.strip()

def build_preamble_header() -> str:
    return (
        "The Constitution of India\n"
        "Preamble"
    )


def build_preamble_body(
    preamble: str,
) -> str:
    return preamble.strip()


def build_schedule_header(
    schedule: dict[str, Any],
) -> str:
    schedule_number = str(
        schedule[
            "schedule_number"
        ]
    ).strip()

    schedule_name = str(
        schedule[
            "schedule_name"
        ]
    ).strip()

    return (
        "The Constitution of India\n"
        f"{schedule_name.title()} Schedule\n"
        f"Schedule number: "
        f"{schedule_number}"
    )


def build_schedule_body(
    schedule: dict[str, Any],
) -> str:
    raw_text = str(
        schedule.get(
            "raw_text",
            "",
        )
    ).strip()

    if not raw_text:
        raise RuntimeError(
            "Schedule has empty text: "
            f"{schedule.get('schedule_name')}"
        )

    return raw_text


async def create_constitution_chunks(
) -> None:
    data = (
        load_parsed_constitution()
    )

    articles: list[
        dict[str, Any]
    ] = data["articles"]

    schedules: list[
        dict[str, Any]
    ] = data["schedules"]

    preamble = data[
        "preamble"
    ]

    async with AsyncSessionLocal() as db:
        try:
            (
                document,
                version,
            ) = (
                await
                get_constitution_context(
                    db
                )
            )

            # ---------------------------------
            # Load Article records
            # ---------------------------------

            result = await db.execute(
                select(Section)
                .where(
                    Section.version_id
                    == version.id
                )
            )

            sections = (
                result.scalars().all()
            )

            if len(sections) != 506:
                raise RuntimeError(
                    "Expected 506 "
                    "Constitution Article "
                    "records in DB, found "
                    f"{len(sections)}."
                )

            section_map = {
                section.section_number:
                    section
                for section
                in sections
            }

            # ---------------------------------
            # Remove ONLY old Constitution
            # chunks.
            # ---------------------------------

            print(
                "Removing old "
                "Constitution chunks..."
            )

            await db.execute(
                delete(LegalChunk)
                .where(
                    LegalChunk.document_id
                    == document.id
                )
            )

            await db.flush()

            new_chunks: list[
                dict[str, Any]
            ] = []

            article_chunk_count = 0
            preamble_chunk_count = 0
            schedule_chunk_count = 0

            active_articles = 0
            omitted_articles = 0

            # ---------------------------------
            # Preamble
            # ---------------------------------

            preamble_chunk_count += (
    add_contextual_chunks(
        new_chunks,
        document_id=(
            document.id
        ),
        act_id=(
            document.act_id
        ),
        version_id=(
            version.id
        ),
        section_id=None,
        header=(
            build_preamble_header()
        ),
        body=(
            build_preamble_body(
                preamble
            )
        ),
    )
)

            # ---------------------------------
            # Articles
            # ---------------------------------

            for article in articles:
                number = str(
                    article[
                        "article_number"
                    ]
                ).strip()

                if article.get(
                    "is_omitted",
                    False,
                ):
                    omitted_articles += 1
                    continue

                active_articles += 1

                section = (
                    section_map.get(
                        number
                    )
                )

                if section is None:
                    raise RuntimeError(
                        "Database Article "
                        f"{number} not found."
                    )

                if (
                    section.text
                    == "[Omitted.]"
                ):
                    raise RuntimeError(
                        "Active parsed Article "
                        f"{number} is marked "
                        "omitted in database."
                    )

                article_chunk_count += (
    add_contextual_chunks(
        new_chunks,
        document_id=(
            document.id
        ),
        act_id=(
            document.act_id
        ),
        version_id=(
            version.id
        ),
        section_id=(
            section.id
        ),
        header=(
            build_article_header(
                article,
                section,
            )
        ),
        body=(
            build_article_body(
                section
            )
        ),
    )
)

            if (
                active_articles
                != EXPECTED_ACTIVE
            ):
                raise RuntimeError(
                    "Unexpected active "
                    "Article count.\n"
                    f"Expected: "
                    f"{EXPECTED_ACTIVE}\n"
                    f"Found: "
                    f"{active_articles}"
                )

            if (
                omitted_articles
                != EXPECTED_OMITTED
            ):
                raise RuntimeError(
                    "Unexpected omitted "
                    "Article count."
                )

            # ---------------------------------
            # Schedules
            # ---------------------------------

            for schedule in schedules:
                schedule_chunk_count += (
    add_contextual_chunks(
        new_chunks,
        document_id=(
            document.id
        ),
        act_id=(
            document.act_id
        ),
        version_id=(
            version.id
        ),
        section_id=None,
        header=(
            build_schedule_header(
                schedule
            )
        ),
        body=(
            build_schedule_body(
                schedule
            )
        ),
    )
)

            # ---------------------------------
            # Global hash collision check
            # BEFORE inserting.
            # ---------------------------------

            hashes = [
                chunk[
                    "content_hash"
                ]
                for chunk
                in new_chunks
            ]

            if (
                len(hashes)
                != len(set(hashes))
            ):
                duplicates = {
                    value
                    for value in hashes
                    if hashes.count(value)
                    > 1
                }

                raise RuntimeError(
                    "Duplicate Constitution "
                    "chunk content hashes "
                    "detected before insert: "
                    f"{len(duplicates)}"
                )

            # ---------------------------------
            # Insert
            # ---------------------------------

            print(
                "\nChunk preparation "
                "complete."
            )

            print(
                f"Active Articles: "
                f"{active_articles}"
            )

            print(
                f"Omitted Articles skipped: "
                f"{omitted_articles}"
            )

            print(
                f"Article chunks: "
                f"{article_chunk_count}"
            )

            print(
                f"Preamble chunks: "
                f"{preamble_chunk_count}"
            )

            print(
                f"Schedule chunks: "
                f"{schedule_chunk_count}"
            )

            print(
                f"Total chunks: "
                f"{len(new_chunks)}"
            )

            for chunk_data in new_chunks:
                db.add(
                    LegalChunk(
                        **chunk_data
                    )
                )

            await db.flush()

            # ---------------------------------
            # Verify count before commit
            # ---------------------------------

            verify_result = (
                await db.execute(
                    select(LegalChunk)
                    .where(
                        LegalChunk.document_id
                        == document.id
                    )
                )
            )

            saved_chunks = (
                verify_result
                .scalars()
                .all()
            )

            if (
                len(saved_chunks)
                != len(new_chunks)
            ):
                raise RuntimeError(
                    "Constitution chunk "
                    "count mismatch before "
                    "commit.\n"
                    f"Prepared: "
                    f"{len(new_chunks)}\n"
                    f"Saved: "
                    f"{len(saved_chunks)}"
                )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    print(
        "\n================================"
    )
    print(
        "Constitution chunking complete."
    )
    print(
        "================================"
    )

    print(
        f"Document ID: "
        f"{document.id}"
    )

    print(
        f"Article chunks: "
        f"{article_chunk_count}"
    )

    print(
        f"Preamble chunks: "
        f"{preamble_chunk_count}"
    )

    print(
        f"Schedule chunks: "
        f"{schedule_chunk_count}"
    )

    print(
        f"Total chunks: "
        f"{len(new_chunks)}"
    )


if __name__ == "__main__":
    asyncio.run(
        create_constitution_chunks()
    )