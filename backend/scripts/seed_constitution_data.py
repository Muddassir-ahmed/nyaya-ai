from __future__ import annotations

import asyncio
from datetime import date
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.act import Act
from app.models.jurisdiction import Jurisdiction
from app.models.legal_document import LegalDocument
from app.models.legal_source import LegalSource
from app.models.legal_version import LegalVersion


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "legal"
    / "central"
)


PRIMARY_PDF = (
    DATA_DIR
    / "constitution_2026_english.pdf"
)

SECONDARY_PDF = (
    DATA_DIR
    / "constitution_2026_hindi_english.pdf"
)


PRIMARY_URL = (
    "https://www.legislative.gov.in/"
    "static/uploads/2025/07/"
    "c9fe9c9b6840524844316f74bb1c556c.pdf"
)

SECONDARY_URL = (
    "https://www.legislative.gov.in/"
    "static/uploads/2025/08/"
    "575648bd8ecb7654db902b93115d35e4.pdf"
)


PRIMARY_SHA256 = (
    "4C8E93689EC245E26DB08E22B5FF3AD"
    "645C98736F0E5B7C8B6638ACD7861F85B"
)

SECONDARY_SHA256 = (
    "F1DD6521F4126323A2D50AE6079C0DADA"
    "5FB4DCAE96B5D15786DDE9F989CEEA2"
)


PUBLISHER = (
    "Legislative Department, "
    "Ministry of Law and Justice, "
    "Government of India"
)


PRIMARY_SOURCE_NAME = (
    "Constitution of India — "
    "Official English Edition "
    "(As on 1 May 2026)"
)

SECONDARY_SOURCE_NAME = (
    "Constitution of India — "
    "Hindi-English Diglot Edition "
    "(As on 1 May 2026)"
)


ACT_NAME = "The Constitution of India"

VERSION_LABEL = (
    "Constitution of India — "
    "As on 1 May 2026"
)

PRIMARY_DOCUMENT_TITLE = (
    "The Constitution of India"
)

SECONDARY_DOCUMENT_TITLE = (
    "The Constitution of India — "
    "Hindi-English Diglot Edition "
    "(As on 1 May 2026)"
)


def calculate_sha256(
    file_path: Path,
) -> str:
    hasher = sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(
            1024 * 1024
        ):
            hasher.update(chunk)

    return hasher.hexdigest().upper()


def verify_locked_file(
    file_path: Path,
    expected_sha256: str,
    label: str,
) -> None:
    if not file_path.exists():
        raise FileNotFoundError(
            f"{label} PDF not found: "
            f"{file_path}"
        )

    actual_sha256 = calculate_sha256(
        file_path
    )

    print(
        f"{label} SHA-256: "
        f"{actual_sha256}"
    )

    if (
        actual_sha256
        != expected_sha256
    ):
        raise RuntimeError(
            f"{label} PDF hash does not "
            "match the locked source.\n"
            f"Expected: {expected_sha256}\n"
            f"Actual:   {actual_sha256}"
        )


async def get_india(
    db: AsyncSession,
) -> Jurisdiction:
    result = await db.execute(
        select(Jurisdiction)
        .where(
            Jurisdiction.code == "IN"
        )
    )

    india = result.scalar_one_or_none()

    if india is None:
        raise RuntimeError(
            "India jurisdiction (IN) "
            "does not exist. Run the "
            "base legal metadata seed first."
        )

    if not india.is_active:
        raise RuntimeError(
            "India jurisdiction exists "
            "but is inactive."
        )

    return india


async def upsert_verified_source(
    db: AsyncSession,
    *,
    name: str,
    url: str,
    jurisdiction_id: int,
    notes: str,
) -> LegalSource:
    result = await db.execute(
        select(LegalSource)
        .where(
            LegalSource.url == url
        )
        .order_by(
            LegalSource.id
        )
    )

    source = result.scalars().first()

    if source is None:
        source = LegalSource(
            name=name,
            publisher=PUBLISHER,
            source_type=(
                "official_government"
            ),
            url=url,
            jurisdiction_id=(
                jurisdiction_id
            ),
            verification_status=(
                "verified"
            ),
            is_active=True,
            notes=notes,
        )

        db.add(source)

    else:
        # Reconcile an existing record with
        # the currently LOCKED metadata.
        source.name = name
        source.publisher = PUBLISHER
        source.source_type = (
            "official_government"
        )
        source.jurisdiction_id = (
            jurisdiction_id
        )
        source.verification_status = (
            "verified"
        )
        source.is_active = True
        source.notes = notes

    await db.flush()

    return source


async def upsert_constitution_act(
    db: AsyncSession,
    *,
    jurisdiction_id: int,
) -> Act:
    result = await db.execute(
        select(Act)
        .where(
            Act.name == ACT_NAME
        )
    )

    act = result.scalar_one_or_none()

    if act is None:
        act = Act(
            name=ACT_NAME,
            short_name="COI",
            act_number=None,
            year=1950,
            act_type="constitution",
            jurisdiction_id=(
                jurisdiction_id
            ),
            description=(
                "The Constitution of India, "
                "represented in NyayaAI using "
                "the official consolidated "
                "edition as on 1 May 2026."
            ),
            status="active",
        )

        db.add(act)

    else:
        act.short_name = "COI"
        act.act_number = None
        act.year = 1950
        act.act_type = "constitution"
        act.jurisdiction_id = (
            jurisdiction_id
        )
        act.description = (
            "The Constitution of India, "
            "represented in NyayaAI using "
            "the official consolidated "
            "edition as on 1 May 2026."
        )
        act.status = "active"

    await db.flush()

    return act


async def upsert_constitution_version(
    db: AsyncSession,
    *,
    act_id: int,
    primary_source_id: int,
) -> LegalVersion:
    result = await db.execute(
        select(LegalVersion)
        .where(
            LegalVersion.act_id == act_id,
            LegalVersion.version_label
            == VERSION_LABEL,
        )
    )

    version = result.scalar_one_or_none()

    notes = (
        "Official consolidated Constitution "
        "snapshot as on 1 May 2026. "
        "The effective_from value represents "
        "the snapshot/reference date of this "
        "consolidated edition and must not be "
        "interpreted as the original "
        "commencement date of the Constitution."
    )

    if version is None:
        version = LegalVersion(
            act_id=act_id,
            version_label=VERSION_LABEL,
            effective_from=date(
                2026,
                5,
                1,
            ),
            effective_until=None,
            status="active",
            source_id=primary_source_id,
            notes=notes,
        )

        db.add(version)

    else:
        version.effective_from = date(
            2026,
            5,
            1,
        )
        version.effective_until = None
        version.status = "active"
        version.source_id = (
            primary_source_id
        )
        version.notes = notes

    await db.flush()

    return version


async def upsert_document(
    db: AsyncSession,
    *,
    act_id: int,
    source_id: int,
    title: str,
    document_type: str,
    file_path: str,
    file_hash: str,
    language: str,
    verification_notes: str,
) -> LegalDocument:
    result = await db.execute(
        select(LegalDocument)
        .where(
            LegalDocument.source_id
            == source_id,
            LegalDocument.title
            == title,
        )
    )

    document = (
        result.scalar_one_or_none()
    )

    if document is None:
        # file_hash is globally unique in
        # legal_documents, so fail early if
        # another record already owns it.
        hash_result = await db.execute(
            select(LegalDocument)
            .where(
                LegalDocument.file_hash
                == file_hash
            )
        )

        hash_owner = (
            hash_result
            .scalar_one_or_none()
        )

        if hash_owner is not None:
            raise RuntimeError(
                "Locked Constitution PDF hash "
                "already belongs to another "
                "LegalDocument.\n"
                f"Document id: {hash_owner.id}\n"
                f"Title: {hash_owner.title}"
            )

        document = LegalDocument(
            act_id=act_id,
            source_id=source_id,
            title=title,
            document_type=document_type,
            file_path=file_path,
            file_hash=file_hash,
            mime_type="application/pdf",
            language=language,
            is_verified=True,
            verification_notes=(
                verification_notes
            ),
        )

        db.add(document)

    else:
        document.act_id = act_id
        document.document_type = (
            document_type
        )
        document.file_path = file_path
        document.file_hash = file_hash
        document.mime_type = (
            "application/pdf"
        )
        document.language = language
        document.is_verified = True
        document.verification_notes = (
            verification_notes
        )

    await db.flush()

    return document


async def seed_constitution_data() -> None:
    print(
        "Verifying locked Constitution "
        "files before database changes..."
    )

    verify_locked_file(
        PRIMARY_PDF,
        PRIMARY_SHA256,
        "Primary English",
    )

    verify_locked_file(
        SECONDARY_PDF,
        SECONDARY_SHA256,
        "Secondary Hindi-English",
    )

    print(
        "Locked Constitution files "
        "verified.\n"
    )

    async with AsyncSessionLocal() as db:
        try:
            india = await get_india(
                db
            )

            primary_source = (
                await upsert_verified_source(
                    db,
                    name=(
                        PRIMARY_SOURCE_NAME
                    ),
                    url=PRIMARY_URL,
                    jurisdiction_id=(
                        india.id
                    ),
                    notes=(
                        "LOCKED canonical "
                        "Constitution ingestion "
                        "source. Official English "
                        "edition, as on "
                        "1 May 2026."
                    ),
                )
            )

            secondary_source = (
                await upsert_verified_source(
                    db,
                    name=(
                        SECONDARY_SOURCE_NAME
                    ),
                    url=SECONDARY_URL,
                    jurisdiction_id=(
                        india.id
                    ),
                    notes=(
                        "LOCKED secondary "
                        "official Hindi-English "
                        "diglot reference. "
                        "Provenance/bilingual "
                        "verification source only; "
                        "not used as the canonical "
                        "English parsing source."
                    ),
                )
            )

            act = (
                await upsert_constitution_act(
                    db,
                    jurisdiction_id=(
                        india.id
                    ),
                )
            )

            version = (
                await
                upsert_constitution_version(
                    db,
                    act_id=act.id,
                    primary_source_id=(
                        primary_source.id
                    ),
                )
            )

            primary_document = (
                await upsert_document(
                    db,
                    act_id=act.id,
                    source_id=(
                        primary_source.id
                    ),
                    title=(
                        PRIMARY_DOCUMENT_TITLE
                    ),
                    document_type=(
                        "constitution"
                    ),
                    file_path=(
                        "data/legal/central/"
                        "constitution_2026_english.pdf"
                    ),
                    file_hash=(
                        PRIMARY_SHA256
                    ),
                    language="en",
                    verification_notes=(
                        "Verified against the "
                        "user-locked official "
                        "Legislative Department "
                        "English PDF. SHA-256 "
                        "checked before seeding."
                    ),
                )
            )

            secondary_document = (
                await upsert_document(
                    db,
                    act_id=act.id,
                    source_id=(
                        secondary_source.id
                    ),
                    title=(
                        SECONDARY_DOCUMENT_TITLE
                    ),
                    document_type=(
                        "constitution_reference"
                    ),
                    file_path=(
                        "data/legal/central/"
                        "constitution_2026_"
                        "hindi_english.pdf"
                    ),
                    file_hash=(
                        SECONDARY_SHA256
                    ),
                    language="hi-en",
                    verification_notes=(
                        "Verified against the "
                        "user-locked official "
                        "Legislative Department "
                        "Hindi-English diglot PDF. "
                        "Reference/provenance only; "
                        "not canonical parser input."
                    ),
                )
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    print(
        "================================"
    )
    print(
        "Constitution metadata seeded."
    )
    print(
        "================================"
    )
    print(
        f"India jurisdiction id: "
        f"{india.id}"
    )
    print(
        f"Primary source id: "
        f"{primary_source.id}"
    )
    print(
        f"Secondary source id: "
        f"{secondary_source.id}"
    )
    print(
        f"Act id: {act.id}"
    )
    print(
        f"Version id: {version.id}"
    )
    print(
        f"Primary document id: "
        f"{primary_document.id}"
    )
    print(
        f"Secondary document id: "
        f"{secondary_document.id}"
    )
    print(
        "Primary source verified: "
        f"{primary_source.verification_status}"
    )
    print(
        "Primary document verified: "
        f"{primary_document.is_verified}"
    )


if __name__ == "__main__":
    asyncio.run(
        seed_constitution_data()
    )