from collections import Counter
from hashlib import sha256

from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument
from app.models.legal_version import LegalVersion
from app.models.section import Section
from app.models.subsection import Subsection
from app.models.clause import Clause


MAX_CHARS = 1800

BNS_DOCUMENT_ID = 2
BNS_ACT_ID = 1
BNS_VERSION_ID = 1

CONSTITUTION_DOCUMENT_IDS = (
    3,
    4,
)

EXPECTED_CONSTITUTION_CHUNKS = 724
EXPECTED_BNS_SECTIONS = 358


def make_hash(
    content: str,
) -> str:
    return sha256(
        content.encode("utf-8")
    ).hexdigest()


def split_text(
    text: str,
    max_chars: int = MAX_CHARS,
) -> list[str]:

    text = text.strip()

    if not text:
        return []

    if len(text) <= max_chars:
        return [
            text
        ]

    chunks = []

    words = text.split()

    current = []
    current_length = 0

    for word in words:

        additional_length = (
            len(word) + 1
        )

        if (
            current
            and (
                current_length
                + additional_length
                > max_chars
            )
        ):
            chunks.append(
                " ".join(current)
            )

            current = []
            current_length = 0

        current.append(
            word
        )

        current_length += (
            additional_length
        )

    if current:
        chunks.append(
            " ".join(current)
        )

    return chunks


def split_parent_text(
    text: str | None,
) -> tuple[str, str]:
    """
    Split DB parent text into:

        statutory body
        illustration content

    ingest_bns_structure.py stores illustrations as:

        <body>

        Illustrations.
        <examples>

    Illustrations remain retrievable but are kept
    separate from the statutory body during chunking.
    """

    if not text:
        return "", ""

    text = text.strip()

    marker = "Illustrations."

    before, separator, after = (
        text.partition(marker)
    )

    if not separator:
        return text, ""

    return (
        before.strip(),
        after.strip(),
    )


def subsection_number_key(
    number: str,
) -> int:
    return int(
        number.strip("()")
    )


def clause_number_key(
    number: str,
) -> str:
    return number.strip(
        "()"
    )


def validate_sections_for_chunking(
    sections,
) -> None:
    """
    Refuse to rebuild chunks unless the BNS hierarchy
    contains exactly Sections 1 through 358.
    """

    try:
        numbers = [
            int(
                section.section_number
            )
            for section in sections
        ]

    except ValueError as exc:
        raise RuntimeError(
            "BNS contains a non-numeric "
            "section number."
        ) from exc

    counts = Counter(
        numbers
    )

    duplicates = sorted(
        number
        for number, count
        in counts.items()
        if count > 1
    )

    expected = set(
        range(
            1,
            EXPECTED_BNS_SECTIONS + 1,
        )
    )

    actual = set(
        numbers
    )

    missing = sorted(
        expected - actual
    )

    outside = sorted(
        actual - expected
    )

    errors = []

    if (
        len(numbers)
        != EXPECTED_BNS_SECTIONS
    ):
        errors.append(
            "Expected "
            f"{EXPECTED_BNS_SECTIONS} "
            "BNS sections, found "
            f"{len(numbers)}."
        )

    if duplicates:
        errors.append(
            "Duplicate sections: "
            + ", ".join(
                str(number)
                for number in duplicates
            )
        )

    if missing:
        errors.append(
            "Missing sections: "
            + ", ".join(
                str(number)
                for number in missing
            )
        )

    if outside:
        errors.append(
            "Out-of-range sections: "
            + ", ".join(
                str(number)
                for number in outside
            )
        )

    if errors:
        raise RuntimeError(
            "BNS chunk validation failed:\n"
            + "\n".join(errors)
        )


def add_chunks(
    chunks: list[dict],
    *,
    document_id: int,
    act_id: int,
    version_id: int,
    section_id: int,
    subsection_id: int | None,
    clause_id: int | None,
    header: str,
    body: str,
) -> None:
    """
    Split only the body while repeating the legal
    reference header on every resulting chunk.

    This prevents continuation chunks from losing
    their Section/Subsection/Clause identity.
    """

    header = header.strip()
    body = body.strip()

    if not body:
        return

    prefix = (
        f"{header}\n\n"
    )

    available_body_chars = (
        MAX_CHARS
        - len(prefix)
    )

    if available_body_chars <= 0:
        raise RuntimeError(
            "Legal chunk header exceeds "
            "the maximum chunk size."
        )

    body_chunks = split_text(
        body,
        max_chars=available_body_chars,
    )

    for index, body_chunk in enumerate(
        body_chunks
    ):

        content = (
            f"{prefix}"
            f"{body_chunk}"
        )

        if len(content) > MAX_CHARS:
            raise RuntimeError(
                "Generated BNS chunk exceeds "
                f"{MAX_CHARS} characters."
            )

        chunks.append(
            {
                "document_id": (
                    document_id
                ),
                "act_id": act_id,
                "version_id": (
                    version_id
                ),
                "section_id": (
                    section_id
                ),
                "subsection_id": (
                    subsection_id
                ),
                "clause_id": (
                    clause_id
                ),
                "chunk_index": index,
                "content": content,
                "token_count": None,
                "content_hash": (
                    make_hash(content)
                ),
            }
        )


def validate_new_chunks(
    chunks: list[dict],
) -> None:
    if not chunks:
        raise RuntimeError(
            "No BNS chunks were generated."
        )

    hashes = [
        chunk["content_hash"]
        for chunk in chunks
    ]

    duplicate_hashes = [
        content_hash
        for content_hash, count
        in Counter(hashes).items()
        if count > 1
    ]

    if duplicate_hashes:
        raise RuntimeError(
            "Duplicate BNS chunk content "
            "was generated."
        )

    for chunk in chunks:

        if (
            chunk["document_id"]
            != BNS_DOCUMENT_ID
        ):
            raise RuntimeError(
                "Generated chunk has an "
                "unexpected document_id."
            )

        if (
            chunk["act_id"]
            != BNS_ACT_ID
        ):
            raise RuntimeError(
                "Generated chunk has an "
                "unexpected act_id."
            )

        if (
            chunk["version_id"]
            != BNS_VERSION_ID
        ):
            raise RuntimeError(
                "Generated chunk has an "
                "unexpected version_id."
            )

        if (
            len(chunk["content"])
            > MAX_CHARS
        ):
            raise RuntimeError(
                "Generated BNS chunk exceeds "
                "MAX_CHARS."
            )


async def get_constitution_counts(
    db,
) -> tuple[int, int]:

    result = await db.execute(
        select(
            func.count(
                LegalChunk.id
            ),
            func.count(
                LegalChunk.embedding
            ),
        )
        .where(
            LegalChunk.document_id.in_(
                CONSTITUTION_DOCUMENT_IDS
            )
        )
    )

    row = result.one()

    return (
        int(row[0]),
        int(row[1]),
    )


async def assert_constitution_unchanged(
    db,
) -> None:

    (
        chunk_count,
        embedded_count,
    ) = await get_constitution_counts(
        db
    )

    if (
        chunk_count
        != EXPECTED_CONSTITUTION_CHUNKS
        or embedded_count
        != EXPECTED_CONSTITUTION_CHUNKS
    ):
        raise RuntimeError(
            "Constitution safety invariant "
            "failed. Expected "
            f"{EXPECTED_CONSTITUTION_CHUNKS} "
            "chunks and embeddings, found "
            f"{chunk_count} chunks and "
            f"{embedded_count} embeddings."
        )


async def create_bns_chunks() -> None:

    async with AsyncSessionLocal() as db:

        try:

            # ---------------------------------------------
            # Resolve canonical BNS document
            # ---------------------------------------------

            document_result = (
                await db.execute(
                    select(
                        LegalDocument
                    )
                    .where(
                        LegalDocument.title
                        == (
                            "The Bharatiya "
                            "Nyaya Sanhita, 2023"
                        )
                    )
                )
            )

            document = (
                document_result
                .scalar_one_or_none()
            )

            if document is None:
                raise RuntimeError(
                    "BNS legal document "
                    "not found."
                )

            if (
                document.id
                != BNS_DOCUMENT_ID
            ):
                raise RuntimeError(
                    "BNS document_id safety "
                    "check failed."
                )

            if (
                document.act_id
                != BNS_ACT_ID
            ):
                raise RuntimeError(
                    "BNS act_id safety "
                    "check failed."
                )

            # ---------------------------------------------
            # Resolve canonical active BNS version
            # ---------------------------------------------

            version_result = (
                await db.execute(
                    select(
                        LegalVersion
                    )
                    .where(
                        LegalVersion.act_id
                        == BNS_ACT_ID,
                        LegalVersion.status
                        == "active",
                    )
                )
            )

            version = (
                version_result
                .scalar_one_or_none()
            )

            if version is None:
                raise RuntimeError(
                    "Active BNS version "
                    "not found."
                )

            if (
                version.id
                != BNS_VERSION_ID
            ):
                raise RuntimeError(
                    "BNS version_id safety "
                    "check failed."
                )

            # ---------------------------------------------
            # Constitution hard safety invariant
            # ---------------------------------------------

            await assert_constitution_unchanged(
                db
            )

            # ---------------------------------------------
            # Load BNS sections
            # ---------------------------------------------

            sections_result = (
                await db.execute(
                    select(
                        Section
                    )
                    .where(
                        Section.version_id
                        == BNS_VERSION_ID
                    )
                )
            )

            sections = list(
                sections_result
                .scalars()
                .all()
            )

            validate_sections_for_chunking(
                sections
            )

            sections.sort(
                key=lambda section: int(
                    section.section_number
                )
            )

            print(
                f"Sections found: "
                f"{len(sections)}"
            )

            # ---------------------------------------------
            # Build chunks in memory FIRST.
            #
            # Nothing is deleted until every section has
            # successfully produced valid chunk data.
            # ---------------------------------------------

            new_chunks: list[dict] = []

            represented_section_ids = set()

            for section in sections:

                chunks_before_section = (
                    len(new_chunks)
                )

                section_header = (
                    f"Section "
                    f"{section.section_number}"
                )

                if section.title:
                    section_header += (
                        f" — "
                        f"{section.title.strip()}"
                    )

                # -----------------------------------------
                # Section-level statutory text /
                # illustrations
                # -----------------------------------------

                (
                    section_body,
                    section_illustrations,
                ) = split_parent_text(
                    section.text
                )

                if section_body:
                    add_chunks(
                        new_chunks,
                        document_id=(
                            BNS_DOCUMENT_ID
                        ),
                        act_id=BNS_ACT_ID,
                        version_id=(
                            BNS_VERSION_ID
                        ),
                        section_id=(
                            section.id
                        ),
                        subsection_id=None,
                        clause_id=None,
                        header=section_header,
                        body=section_body,
                    )

                if section_illustrations:
                    add_chunks(
                        new_chunks,
                        document_id=(
                            BNS_DOCUMENT_ID
                        ),
                        act_id=BNS_ACT_ID,
                        version_id=(
                            BNS_VERSION_ID
                        ),
                        section_id=(
                            section.id
                        ),
                        subsection_id=None,
                        clause_id=None,
                        header=(
                            f"{section_header}\n"
                            "Illustrations"
                        ),
                        body=(
                            section_illustrations
                        ),
                    )

                # -----------------------------------------
                # Subsections
                # -----------------------------------------

                subsections_result = (
                    await db.execute(
                        select(
                            Subsection
                        )
                        .where(
                            Subsection.section_id
                            == section.id
                        )
                    )
                )

                subsections = list(
                    subsections_result
                    .scalars()
                    .all()
                )

                subsections.sort(
                    key=lambda subsection: (
                        subsection_number_key(
                            subsection
                            .subsection_number
                        )
                    )
                )

                for subsection in subsections:

                    subsection_header = (
                        f"{section_header}\n"
                        f"Subsection "
                        f"{subsection.subsection_number}"
                    )

                    (
                        subsection_body,
                        subsection_illustrations,
                    ) = split_parent_text(
                        subsection.text
                    )

                    # Always preserve the parent
                    # subsection text, even when it
                    # also contains Clause rows.
                    if subsection_body:
                        add_chunks(
                            new_chunks,
                            document_id=(
                                BNS_DOCUMENT_ID
                            ),
                            act_id=BNS_ACT_ID,
                            version_id=(
                                BNS_VERSION_ID
                            ),
                            section_id=(
                                section.id
                            ),
                            subsection_id=(
                                subsection.id
                            ),
                            clause_id=None,
                            header=(
                                subsection_header
                            ),
                            body=(
                                subsection_body
                            ),
                        )

                    if (
                        subsection_illustrations
                    ):
                        add_chunks(
                            new_chunks,
                            document_id=(
                                BNS_DOCUMENT_ID
                            ),
                            act_id=BNS_ACT_ID,
                            version_id=(
                                BNS_VERSION_ID
                            ),
                            section_id=(
                                section.id
                            ),
                            subsection_id=(
                                subsection.id
                            ),
                            clause_id=None,
                            header=(
                                f"{subsection_header}\n"
                                "Illustrations"
                            ),
                            body=(
                                subsection_illustrations
                            ),
                        )

                    # -------------------------------------
                    # Clauses
                    # -------------------------------------

                    clauses_result = (
                        await db.execute(
                            select(
                                Clause
                            )
                            .where(
                                Clause.subsection_id
                                == subsection.id
                            )
                        )
                    )

                    clauses = list(
                        clauses_result
                        .scalars()
                        .all()
                    )

                    clauses.sort(
                        key=lambda clause: (
                            clause_number_key(
                                clause.clause_number
                            )
                        )
                    )

                    for clause in clauses:

                        if not clause.text:
                            continue

                        clause_parts = []

                        # A clause may depend on the
                        # introductory words of its
                        # parent subsection.
                        #
                        # Repeat only the statutory
                        # subsection body here.
                        # Do NOT repeat illustrations.
                        if subsection_body:
                            clause_parts.append(
                                "Subsection context:\n"
                                f"{subsection_body}"
                            )

                        clause_parts.append(
                            "Clause text:\n"
                            f"{clause.text.strip()}"
                        )

                        add_chunks(
                            new_chunks,
                            document_id=(
                                BNS_DOCUMENT_ID
                            ),
                            act_id=BNS_ACT_ID,
                            version_id=(
                                BNS_VERSION_ID
                            ),
                            section_id=(
                                section.id
                            ),
                            subsection_id=(
                                subsection.id
                            ),
                            clause_id=(
                                clause.id
                            ),
                            header=(
                                f"{subsection_header}\n"
                                f"Clause "
                                f"{clause.clause_number}"
                            ),
                            body="\n\n".join(
                                clause_parts
                            ),
                        )

                if (
                    len(new_chunks)
                    == chunks_before_section
                ):
                    raise RuntimeError(
                        "BNS Section "
                        f"{section.section_number} "
                        "produced no chunks."
                    )

                represented_section_ids.add(
                    section.id
                )

            if (
                len(represented_section_ids)
                != EXPECTED_BNS_SECTIONS
            ):
                raise RuntimeError(
                    "Not all 358 BNS sections "
                    "produced chunks."
                )

            validate_new_chunks(
                new_chunks
            )

            print(
                f"New chunks prepared: "
                f"{len(new_chunks)}"
            )

            # ---------------------------------------------
            # Delete ONLY old BNS chunks.
            # ---------------------------------------------

            print(
                "Removing old BNS chunks..."
            )

            await db.execute(
                delete(
                    LegalChunk
                )
                .where(
                    LegalChunk.document_id
                    == BNS_DOCUMENT_ID
                )
            )

            await db.flush()

            # ---------------------------------------------
            # Protect the global unique content_hash.
            # ---------------------------------------------

            new_hashes = [
                chunk["content_hash"]
                for chunk in new_chunks
            ]

            collision_result = (
                await db.execute(
                    select(
                        LegalChunk.content_hash
                    )
                    .where(
                        LegalChunk.document_id
                        != BNS_DOCUMENT_ID,
                        LegalChunk.content_hash.in_(
                            new_hashes
                        ),
                    )
                )
            )

            collisions = (
                collision_result
                .scalars()
                .all()
            )

            if collisions:
                raise RuntimeError(
                    "One or more new BNS chunks "
                    "collide with existing "
                    "non-BNS content hashes."
                )

            # ---------------------------------------------
            # Insert corrected BNS chunks.
            # ---------------------------------------------

            for chunk_data in new_chunks:
                db.add(
                    LegalChunk(
                        **chunk_data
                    )
                )

            await db.flush()

            # ---------------------------------------------
            # Verify BNS count before commit.
            # ---------------------------------------------

            count_result = (
                await db.execute(
                    select(
                        func.count(
                            LegalChunk.id
                        )
                    )
                    .where(
                        LegalChunk.document_id
                        == BNS_DOCUMENT_ID
                    )
                )
            )

            stored_bns_chunks = (
                count_result.scalar_one()
            )

            if (
                stored_bns_chunks
                != len(new_chunks)
            ):
                raise RuntimeError(
                    "Stored BNS chunk count "
                    "does not match generated "
                    "chunk count."
                )

            # Constitution must still be exactly
            # 724/724 before commit.
            await assert_constitution_unchanged(
                db
            )

            await db.commit()

            print(
                "\nBNS chunk creation completed."
            )

            print(
                f"Chunks created: "
                f"{len(new_chunks)}"
            )

            print(
                "Constitution invariant: "
                "724 chunks / 724 embeddings"
            )

        except Exception:

            await db.rollback()

            raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        create_bns_chunks()
    )