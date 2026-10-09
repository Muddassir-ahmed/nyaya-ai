from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.act import Act
from app.models.clause import Clause
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument
from app.models.legal_source import LegalSource
from app.models.legal_version import LegalVersion
from app.models.section import Section
from app.models.subsection import Subsection
from app.schemas.legal_evidence import LegalEvidence


async def build_legal_evidence(
    db: AsyncSession,
    chunks: list[LegalChunk],
) -> list[LegalEvidence]:

    if not chunks:
        return []

    evidence: list[LegalEvidence] = []

    for chunk in chunks:

        result = await db.execute(
            select(
                LegalChunk,
                Act,
                LegalVersion,
                Section,
                Subsection,
                Clause,
                LegalDocument,
                LegalSource,
            )
            .join(
                Act,
                LegalChunk.act_id == Act.id,
                isouter=True,
            )
            .join(
                LegalVersion,
                LegalChunk.version_id == LegalVersion.id,
                isouter=True,
            )
            .join(
                Section,
                LegalChunk.section_id == Section.id,
                isouter=True,
            )
            .join(
                Subsection,
                LegalChunk.subsection_id == Subsection.id,
                isouter=True,
            )
            .join(
                Clause,
                LegalChunk.clause_id == Clause.id,
                isouter=True,
            )
            .join(
                LegalDocument,
                LegalChunk.document_id == LegalDocument.id,
                isouter=True,
            )
            .join(
                LegalSource,
                LegalDocument.source_id == LegalSource.id,
                isouter=True,
            )
            .where(
                LegalChunk.id == chunk.id
            )
        )

        row = result.first()

        if row is None:
            continue

        (
            db_chunk,
            act,
            version,
            section,
            subsection,
            clause,
            document,
            source,
        ) = row

        evidence.append(
    LegalEvidence(
        chunk_id=db_chunk.id,
        content=db_chunk.content,

        document_title=(
            document.title
            if document
            else None
        ),

        document_type=(
            document.document_type
            if document
            else None
        ),

        act_name=(
            act.name
            if act
            else None
        ),

        act_short_name=(
            act.short_name
            if act
            else None
        ),

                version_label=(
                    version.version_label
                    if version
                    else None
                ),

                section_number=(
                    section.section_number
                    if section
                    else None
                ),

                section_title=(
                    section.title
                    if section
                    else None
                ),

                subsection_number=(
                    subsection.subsection_number
                    if subsection
                    else None
                ),

                clause_number=(
                    clause.clause_number
                    if clause
                    else None
                ),

                source_name=(
                    source.name
                    if source
                    else None
                ),

                source_publisher=(
                    source.publisher
                    if source
                    else None
                ),

                source_url=(
                    source.url
                    if source
                    else None
                ),

                publication_date=(
                    source.publication_date
                    if source
                    else None
                ),

                retrieved_at=(
                    source.retrieved_at
                    if source
                    else None
                ),

                is_verified=(
                    document.is_verified
                    if document
                    else False
                ),
            )
        )

    return evidence