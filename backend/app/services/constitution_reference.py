from __future__ import annotations

from dataclasses import dataclass, field
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.act import Act
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument
from app.models.legal_version import LegalVersion
from app.models.section import Section


CONSTITUTION_ACT_NAME = (
    "The Constitution of India"
)

CONSTITUTION_DOCUMENT_TITLE = (
    "The Constitution of India"
)

CONSTITUTION_VERSION_LABEL = (
    "Constitution of India — "
    "As on 1 May 2026"
)


ARTICLE_REFERENCE_PATTERN = re.compile(
    r"\b(?:article|art\.?)\s*"
    r"("
    r"\d{1,3}"
    r"[A-Za-z]{0,2}"
    r"(?:\s*-\s*[A-Za-z]{1,2})?"
    r")"
    r"\b",
    re.IGNORECASE,
)

PREAMBLE_REFERENCE_PATTERN = re.compile(
    r"\bpreamble\b",
    re.IGNORECASE,
)


@dataclass
class ConstitutionContext:
    act_id: int
    version_id: int
    document_id: int


@dataclass
class ConstitutionArticleResolution:
    matched: bool

    requested_number: str | None = None
    canonical_number: str | None = None

    act_id: int | None = None
    version_id: int | None = None
    document_id: int | None = None
    section_id: int | None = None

    is_omitted: bool = False

    chunks: list[LegalChunk] = field(
        default_factory=list
    )


@dataclass
class ConstitutionPreambleResolution:
    act_id: int
    version_id: int
    document_id: int

    chunks: list[LegalChunk] = field(
        default_factory=list
    )


def normalize_article_identifier(
    value: str,
) -> str:
    """
    Normalize Article identifiers only for
    comparison.

    Examples:

        21       -> 21
        21A      -> 21A
        243-I    -> 243I
        243 I    -> 243I
        243Z-I   -> 243ZI
        239AA    -> 239AA

    The canonical database identifier is NOT
    modified.
    """

    return re.sub(
        r"[\s-]+",
        "",
        value.upper().strip(),
    )


def extract_article_reference(
    query: str,
) -> str | None:
    match = ARTICLE_REFERENCE_PATTERN.search(
        query
    )

    if match is None:
        return None

    return match.group(1).strip()


async def get_constitution_context(
    db: AsyncSession,
) -> ConstitutionContext:
    act_result = await db.execute(
        select(Act)
        .where(
            Act.name
            == CONSTITUTION_ACT_NAME,

            Act.act_type
            == "constitution",

            Act.status
            == "active",
        )
    )

    acts = act_result.scalars().all()

    if len(acts) != 1:
        raise RuntimeError(
            "Expected exactly one active "
            "Constitution Act, found "
            f"{len(acts)}."
        )

    act = acts[0]

    version_result = await db.execute(
        select(LegalVersion)
        .where(
            LegalVersion.act_id
            == act.id,

            LegalVersion.version_label
            == CONSTITUTION_VERSION_LABEL,

            LegalVersion.status
            == "active",
        )
    )

    versions = (
        version_result.scalars().all()
    )

    if len(versions) != 1:
        raise RuntimeError(
            "Expected exactly one active "
            "Constitution version, found "
            f"{len(versions)}."
        )

    version = versions[0]

    document_result = await db.execute(
        select(LegalDocument)
        .where(
            LegalDocument.act_id
            == act.id,

            LegalDocument.title
            == CONSTITUTION_DOCUMENT_TITLE,

            LegalDocument.document_type
            == "constitution",

            LegalDocument.is_verified.is_(
                True
            ),
        )
    )

    documents = (
        document_result.scalars().all()
    )

    if len(documents) != 1:
        raise RuntimeError(
            "Expected exactly one verified "
            "canonical Constitution document, "
            f"found {len(documents)}."
        )

    document = documents[0]

    return ConstitutionContext(
        act_id=act.id,
        version_id=version.id,
        document_id=document.id,
    )


async def resolve_constitution_article(
    db: AsyncSession,
    query: str,
    *,
    top_k: int = 5,
) -> ConstitutionArticleResolution | None:
    """
    Resolve an explicit Article reference
    directly against the structured
    Constitution hierarchy.

    This bypasses semantic guessing for queries
    such as:

        What does Article 21 say?
        Explain Article 243-I.
        What is Article 238?

    Omitted Articles return a successful
    structured match with zero semantic chunks.
    """

    requested_number = (
        extract_article_reference(
            query
        )
    )

    if requested_number is None:
        return None

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    context = (
        await get_constitution_context(
            db
        )
    )

    normalized_requested = (
        normalize_article_identifier(
            requested_number
        )
    )

    # Compare against a normalized form of the
    # canonical section_number.
    #
    # We keep the stored identifier untouched:
    #
    #   243-I
    #   243Z-I
    #
    # and only remove spaces/hyphens while
    # resolving the user's reference.

    normalized_db_number = func.upper(
        func.replace(
            func.replace(
                Section.section_number,
                "-",
                "",
            ),
            " ",
            "",
        )
    )

    section_result = await db.execute(
        select(Section)
        .where(
            Section.version_id
            == context.version_id,

            normalized_db_number
            == normalized_requested,
        )
    )

    sections = (
        section_result.scalars().all()
    )

    # Explicit Article syntax was detected,
    # but that Article does not exist in this
    # Constitution version.
    #
    # Do NOT claim a match.
    if not sections:
        return ConstitutionArticleResolution(
            matched=False,
            requested_number=(
                requested_number
            ),
            act_id=context.act_id,
            version_id=context.version_id,
            document_id=context.document_id,
        )

    if len(sections) != 1:
        raise RuntimeError(
            "Article reference resolved to "
            "multiple Constitution records: "
            f"{requested_number}"
        )

    section = sections[0]

    canonical_number = (
        section.section_number
    )

    is_omitted = (
        section.text.strip()
        == "[Omitted.]"
    )

    # Omitted provisions intentionally have
    # zero retrieval chunks.
    if is_omitted:
        return ConstitutionArticleResolution(
            matched=True,
            requested_number=(
                requested_number
            ),
            canonical_number=(
                canonical_number
            ),
            act_id=context.act_id,
            version_id=context.version_id,
            document_id=context.document_id,
            section_id=section.id,
            is_omitted=True,
            chunks=[],
        )

    chunks_result = await db.execute(
        select(LegalChunk)
        .where(
            LegalChunk.document_id
            == context.document_id,

            LegalChunk.version_id
            == context.version_id,

            LegalChunk.section_id
            == section.id,
        )
        .order_by(
            LegalChunk.chunk_index,
            LegalChunk.id,
        )
        .limit(top_k)
    )

    chunks = (
        chunks_result.scalars().all()
    )

    if not chunks:
        raise RuntimeError(
            "Active Constitution Article "
            f"{canonical_number} has no "
            "retrieval chunks."
        )

    return ConstitutionArticleResolution(
        matched=True,
        requested_number=(
            requested_number
        ),
        canonical_number=(
            canonical_number
        ),
        act_id=context.act_id,
        version_id=context.version_id,
        document_id=context.document_id,
        section_id=section.id,
        is_omitted=False,
        chunks=list(chunks),
    )


def has_explicit_preamble_reference(
    query: str,
) -> bool:
    return (
        PREAMBLE_REFERENCE_PATTERN.search(query)
        is not None
    )


def _is_constitution_preamble_chunk(
    content: str,
) -> bool:
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    if len(lines) < 2:
        return False

    return (
        lines[0].casefold()
        == CONSTITUTION_ACT_NAME.casefold()
        and lines[1].casefold()
        == "preamble"
    )


async def resolve_constitution_preamble(
    db: AsyncSession,
    query: str,
    *,
    top_k: int = 5,
) -> ConstitutionPreambleResolution | None:
    """
    Resolve an explicit Constitution Preamble
    reference directly against the verified
    canonical Constitution document.

    This avoids semantic retrieval adding unrelated
    Articles when the user explicitly asks about
    the Preamble.
    """

    if not has_explicit_preamble_reference(
        query
    ):
        return None

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    context = (
        await get_constitution_context(
            db
        )
    )

    result = await db.execute(
        select(LegalChunk)
        .where(
            LegalChunk.document_id
            == context.document_id,

            LegalChunk.version_id
            == context.version_id,

            LegalChunk.section_id.is_(None),
        )
        .order_by(
            LegalChunk.chunk_index,
            LegalChunk.id,
        )
    )

    document_level_chunks = (
        result.scalars().all()
    )

    preamble_chunks = [
        chunk
        for chunk in document_level_chunks
        if _is_constitution_preamble_chunk(
            chunk.content
        )
    ]

    if not preamble_chunks:
        raise RuntimeError(
            "Explicit Constitution Preamble "
            "reference was detected, but no "
            "canonical Preamble chunk was found."
        )

    return ConstitutionPreambleResolution(
        act_id=context.act_id,
        version_id=context.version_id,
        document_id=context.document_id,
        chunks=list(
            preamble_chunks[:top_k]
        ),
    )
