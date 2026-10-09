import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.act import Act
from app.models.legal_document import LegalDocument
from app.models.legal_source import LegalSource
from app.models.legal_version import LegalVersion


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
            act_result.scalar_one_or_none()
        )

        if act is None:
            raise RuntimeError(
                "Constitution Act not found."
            )

        version_result = await db.execute(
            select(LegalVersion)
            .where(
                LegalVersion.act_id
                == act.id
            )
        )

        versions = (
            version_result.scalars().all()
        )

        document_result = await db.execute(
            select(LegalDocument)
            .where(
                LegalDocument.act_id
                == act.id
            )
            .order_by(
                LegalDocument.id
            )
        )

        documents = (
            document_result.scalars().all()
        )

        source_ids = {
            document.source_id
            for document in documents
        }

        source_result = await db.execute(
            select(LegalSource)
            .where(
                LegalSource.id.in_(
                    source_ids
                )
            )
            .order_by(
                LegalSource.id
            )
        )

        sources = (
            source_result.scalars().all()
        )

        print(
            f"Act: {act.id} | "
            f"{act.name} | "
            f"type={act.act_type} | "
            f"status={act.status}"
        )

        print("\nVersions:")

        for version in versions:
            print(
                f"{version.id} | "
                f"{version.version_label} | "
                f"from={version.effective_from} | "
                f"status={version.status} | "
                f"source_id={version.source_id}"
            )

        print("\nSources:")

        for source in sources:
            print(
                f"{source.id} | "
                f"{source.name} | "
                f"{source.verification_status} | "
                f"active={source.is_active}"
            )

        print("\nDocuments:")

        for document in documents:
            print(
                f"{document.id} | "
                f"{document.title} | "
                f"type={document.document_type} | "
                f"lang={document.language} | "
                f"verified={document.is_verified} | "
                f"hash={document.file_hash}"
            )


if __name__ == "__main__":
    asyncio.run(main())