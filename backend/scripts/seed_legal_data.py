from datetime import date
from app.models.legal_source import LegalSource
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.jurisdiction import Jurisdiction
from app.models.legal_source import LegalSource
from app.models.act import Act
from app.models.legal_version import LegalVersion
from app.models.section import Section
from app.models.subsection import Subsection
from app.models.clause import Clause
from app.models.legal_document import LegalDocument

async def get_or_create_jurisdiction(
    db: AsyncSession,
    name: str,
    code: str,
    jurisdiction_type: str,
    parent_id: int | None = None,
) -> Jurisdiction:

    result = await db.execute(
        select(Jurisdiction).where(
            Jurisdiction.code == code
        )
    )

    jurisdiction = result.scalar_one_or_none()

    if jurisdiction:
        return jurisdiction

    jurisdiction = Jurisdiction(
        name=name,
        code=code,
        type=jurisdiction_type,
        parent_id=parent_id,
        country_code="IN",
        is_active=True,
    )

    db.add(jurisdiction)
    await db.flush()

    return jurisdiction


async def get_or_create_legal_source(
    db: AsyncSession,
    name: str,
    publisher: str,
    source_type: str,
    url: str,
    jurisdiction_id: int | None = None,
) -> LegalSource:

    result = await db.execute(
        select(LegalSource).where(
            LegalSource.url == url
        )
    )

    source = result.scalar_one_or_none()

    if source:
        return source

    source = LegalSource(
        name=name,
        publisher=publisher,
        source_type=source_type,
        url=url,
        jurisdiction_id=jurisdiction_id,
        verification_status="unverified",
        is_active=True,
    )

    db.add(source)
    await db.flush()

    return source

async def get_or_create_act(
    db: AsyncSession,
    name: str,
    short_name: str | None,
    act_number: str | None,
    year: int | None,
    act_type: str,
    jurisdiction_id: int,
    description: str | None = None,
) -> Act:

    result = await db.execute(
        select(Act).where(
            Act.name == name
        )
    )

    act = result.scalar_one_or_none()

    if act:
        return act

    act = Act(
        name=name,
        short_name=short_name,
        act_number=act_number,
        year=year,
        act_type=act_type,
        jurisdiction_id=jurisdiction_id,
        description=description,
        status="active",
    )

    db.add(act)
    await db.flush()

    return act

async def get_or_create_legal_version(
    db: AsyncSession,
    act_id: int,
    version_label: str,
    effective_from,
    effective_until=None,
    status: str = "active",
    source_id: int | None = None,
    notes: str | None = None,
) -> LegalVersion:

    result = await db.execute(
        select(LegalVersion).where(
            LegalVersion.act_id == act_id,
            LegalVersion.version_label == version_label,
        )
    )

    version = result.scalar_one_or_none()

    if version:
        return version

    version = LegalVersion(
        act_id=act_id,
        version_label=version_label,
        effective_from=effective_from,
        effective_until=effective_until,
        status=status,
        source_id=source_id,
        notes=notes,
    )

    db.add(version)
    await db.flush()

    return version

async def get_or_create_legal_document(
    db: AsyncSession,
    act_id: int | None,
    source_id: int,
    title: str,
    document_type: str,
    file_path: str | None = None,
    mime_type: str | None = None,
    language: str = "en",
) -> LegalDocument:

    result = await db.execute(
        select(LegalDocument).where(
            LegalDocument.title == title,
            LegalDocument.source_id == source_id,
        )
    )

    document = result.scalar_one_or_none()

    if document:
        return document

    document = LegalDocument(
        act_id=act_id,
        source_id=source_id,
        title=title,
        document_type=document_type,
        file_path=file_path,
        mime_type=mime_type,
        language=language,
        is_verified=False,
    )

    db.add(document)
    await db.flush()

    return document

async def get_or_create_section(
    db: AsyncSession,
    version_id: int,
    section_number: str,
    title: str,
    text: str,
) -> Section:

    result = await db.execute(
        select(Section).where(
            Section.version_id == version_id,
            Section.section_number == section_number,
        )
    )

    section = result.scalar_one_or_none()

    if section:
        return section

    section = Section(
        version_id=version_id,
        section_number=section_number,
        title=title,
        text=text,
    )

    db.add(section)
    await db.flush()

    return section

async def get_or_create_subsection(
    db: AsyncSession,
    section_id: int,
    subsection_number: str,
    text: str,
) -> Subsection:

    result = await db.execute(
        select(Subsection).where(
            Subsection.section_id == section_id,
            Subsection.subsection_number == subsection_number,
        )
    )

    subsection = result.scalar_one_or_none()

    if subsection:
        return subsection

    subsection = Subsection(
        section_id=section_id,
        subsection_number=subsection_number,
        text=text,
    )

    db.add(subsection)
    await db.flush()

    return subsection

async def get_or_create_clause(
    db: AsyncSession,
    subsection_id: int,
    clause_number: str,
    text: str,
) -> Clause:

    result = await db.execute(
        select(Clause).where(
            Clause.subsection_id == subsection_id,
            Clause.clause_number == clause_number,
        )
    )

    clause = result.scalar_one_or_none()

    if clause:
        return clause

    clause = Clause(
        subsection_id=subsection_id,
        clause_number=clause_number,
        text=text,
    )

    db.add(clause)
    await db.flush()

    return clause


async def seed_legal_metadata():
    async with AsyncSessionLocal() as db:

        india = await get_or_create_jurisdiction(
            db=db,
            name="India",
            code="IN",
            jurisdiction_type="country",
        )

        await get_or_create_jurisdiction(
            db=db,
            name="Assam",
            code="IN-AS",
            jurisdiction_type="state",
            parent_id=india.id,
        )

        bns_source = await get_or_create_legal_source(
    db=db,
    name="Bharatiya Nyaya Sanhita, 2023 — Gazette",
    publisher="Ministry of Home Affairs, Government of India",
    source_type="official_government",
    url="https://www.mha.gov.in/sites/default/files/250883_english_01042024.pdf",
    jurisdiction_id=india.id,
)

        bns_act = await get_or_create_act(
            db=db,
            name="Bharatiya Nyaya Sanhita, 2023",
            short_name="BNS",
            act_number="45 of 2023",
            year=2023,
            act_type="act",
            jurisdiction_id=india.id,
            description=(
                "An Act to consolidate and amend the provisions relating "
                "to offences and matters connected therewith."
            ),
        )

        bns_version = await get_or_create_legal_version(
            db=db,
            act_id=bns_act.id,
            version_label="BNS 2023 — Original",
            effective_from=date(2024, 7, 1),
            effective_until=None,
            status="active",
            source_id=bns_source.id,
            notes="Initial version of the Bharatiya Nyaya Sanhita, 2023.",
        )

        bns_document = await get_or_create_legal_document(
            db=db,
            act_id=bns_act.id,
            source_id=bns_source.id,
            title="The Bharatiya Nyaya Sanhita, 2023",
            document_type="act",
            mime_type="application/pdf",
            language="en",
        )

        section_1 = await get_or_create_section(
    db=db,
    version_id=bns_version.id,
    section_number="1",
    title="Short title, commencement and application",
    text="PLACEHOLDER — authoritative text will be populated by the legal-source ingestion pipeline.",
)
        subsection_1_1 = await get_or_create_subsection(
    db=db,
    section_id=section_1.id,
    subsection_number="(1)",
    text="PLACEHOLDER — authoritative text will be populated by the legal-source ingestion pipeline.",
)
        await get_or_create_clause(
    db=db,
    subsection_id=subsection_1_1.id,
    clause_number="(a)",
    text="PLACEHOLDER — authoritative text will be populated by the legal-source ingestion pipeline.",
)

        await get_or_create_section(
            db=db,
            version_id=bns_version.id,
            section_number="2",
            title="Definitions",
            text="Definitions and interpretation applicable under the Sanhita.",
        )

        await get_or_create_section(
            db=db,
            version_id=bns_version.id,
            section_number="3",
            title="General explanations",
            text="General explanations applicable to offences under the Sanhita.",
        )


        await db.commit()

        print("Legal metadata seeded successfully.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_legal_metadata())
