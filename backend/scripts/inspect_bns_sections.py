import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.section import Section
from app.models.legal_version import LegalVersion


async def inspect_bns_sections() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Section)
            .join(
                LegalVersion,
                Section.version_id == LegalVersion.id,
            )
            .where(
                LegalVersion.status == "active",
            )
            .order_by(
                Section.section_number,
            )
        )

        sections = result.scalars().all()

    print("=" * 80)
    print("NYAYAAI — BNS SECTION INSPECTION")
    print("=" * 80)

    print(f"\nTotal active sections: {len(sections)}\n")

    for section in sections:
        print(
            f"Section {section.section_number}: "
            f"{section.title}"
        )


if __name__ == "__main__":
    asyncio.run(inspect_bns_sections())