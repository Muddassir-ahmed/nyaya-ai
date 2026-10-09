from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.emergency_contact import EmergencyContact


EMERGENCY_CONTACTS = [
    {
        "name": "Emergency Response Support System (ERSS)",
        "emergency_type": "other",
        "phone_number": "112",
        "jurisdiction": "India",
        "primary_source_name": (
            "Ministry of Home Affairs — Emergency Response Support System (ERSS)"
        ),
        "primary_source_url": (
            "https://www.mha.gov.in/en/commoncontent/"
            "emergency-response-support-system-erss"
        ),
        "secondary_source_name": "C-DAC — Emergency Response Support System",
        "secondary_source_url": (
            "https://cdac.gov.in/index.aspx?id=blog_ni_erss"
        ),
        "verification_notes": (
            "Source pair personally verified and locked before insertion. "
            "112 is the universal emergency fallback."
        ),
    },
    {
        "name": "Child Helpline",
        "emergency_type": "child_safety",
        "phone_number": "1098",
        "jurisdiction": "India",
        "primary_source_name": (
            "SPNIWCD / Ministry of Women and Child Development — Child Helpline"
        ),
        "primary_source_url": (
            "https://www.spniwcd.wcd.gov.in/child-helpline"
        ),
        "secondary_source_name": (
            "Press Information Bureau — Ministry of Women and Child Development"
        ),
        "secondary_source_url": (
            "https://www.pib.gov.in/Pressreleaseshare.aspx?"
            "PRID=1933794&lang=2&reg=48"
        ),
        "verification_notes": (
            "Source pair personally verified and locked before insertion."
        ),
    },
    {
        "name": "Women Helpline",
        "emergency_type": "women_safety",
        "phone_number": "181",
        "jurisdiction": "India",
        "primary_source_name": (
            "Mission Shakti — Women Helpline Statistics"
        ),
        "primary_source_url": (
            "https://missionshakti.wcd.gov.in/statisticsWhl"
        ),
        "secondary_source_name": (
            "SPNIWCD / Ministry of Women and Child Development — Help"
        ),
        "secondary_source_url": "https://spniwcd.wcd.gov.in/help",
        "verification_notes": (
            "Source pair personally verified and locked before insertion."
        ),
    },
    {
        "name": "National Cyber Crime Helpline",
        "emergency_type": "cybercrime",
        "phone_number": "1930",
        "jurisdiction": "India",
        "primary_source_name": (
            "National Cyber Crime Reporting Portal / Indian Cybercrime "
            "Coordination Centre (I4C)"
        ),
        "primary_source_url": (
            "https://www.cybercrime.gov.in/Hindi/Helplinehn.aspx"
        ),
        "secondary_source_name": (
            "Ministry of Home Affairs / Press Information Bureau"
        ),
        "secondary_source_url": (
            "https://www.pib.gov.in/PressReleasePage.aspx?"
            "PRID=2290377&lang=2&reg=48"
        ),
        "verification_notes": (
            "Source pair personally verified and locked before insertion."
        ),
    },
    {
        "name": "Fire Services Helpline",
        "emergency_type": "fire",
        "phone_number": "101",
        "jurisdiction": "India",
        "primary_source_name": (
            "National Portal of India — Helpline Directory"
        ),
        "primary_source_url": (
            "https://www.india.gov.in/directory/helpline"
        ),
        "secondary_source_name": (
            "Government of NCT Delhi — Fire Services"
        ),
        "secondary_source_url": (
            "https://delhi.gov.in/page/fire-services"
        ),
        "verification_notes": (
            "Source pair personally verified and locked before insertion."
        ),
    },
    {
        "name": "Police Helpline",
        "emergency_type": "police",
        "phone_number": "100",
        "jurisdiction": "India",
        "primary_source_name": (
            "National Portal of India — Helpline Directory"
        ),
        "primary_source_url": (
            "https://www.india.gov.in/directory/helpline"
        ),
        "secondary_source_name": (
            "Government of Assam — Helpline Numbers"
        ),
        "secondary_source_url": (
            "https://gad.assam.gov.in/all-helplines-numbers"
        ),
        "verification_notes": (
            "Source pair personally verified and locked before insertion. "
            "112 remains the unified emergency fallback."
        ),
    },
    {
        "name": "108 Mrityunjoy Emergency Response Service — Assam",
        "emergency_type": "medical",
        "phone_number": "108",
        "jurisdiction": "Assam",
        "primary_source_name": (
            "National Health Mission Assam — Integrated 108 Mrityunjoy "
            "Emergency Response Service"
        ),
        "primary_source_url": (
            "https://nhm.assam.gov.in/schemes/detail/"
            "integrated-108-mrityunjoy-emergency-response-service"
        ),
        "secondary_source_name": None,
        "secondary_source_url": None,
        "verification_notes": (
            "Assam-specific source personally verified and locked. "
            "Not treated as an India-wide 108 record."
        ),
    },
    {
        "name": "108 Emergency Ambulance Service — Odisha",
        "emergency_type": "medical",
        "phone_number": "108",
        "jurisdiction": "Odisha",
        "primary_source_name": (
            "National Health Mission Odisha — 108 Services"
        ),
        "primary_source_url": (
            "https://nhmodisha.gov.in/108_services/"
        ),
        "secondary_source_name": None,
        "secondary_source_url": None,
        "verification_notes": (
            "Odisha-specific source personally verified and locked. "
            "Not treated as an India-wide 108 record."
        ),
    },
    {
        "name": "National Ambulance Service 102",
        "emergency_type": "medical",
        "phone_number": "102",
        "jurisdiction": "India",
        "primary_source_name": (
            "National Health Mission — ERS / Patient Transport Service"
        ),
        "primary_source_url": (
            "https://www.nhm.gov.in/index1.php?"
            "lang=1&level=2&lid=189&sublinkid=1217"
        ),
        "secondary_source_name": None,
        "secondary_source_url": None,
        "verification_notes": (
            "National Health Mission source personally verified and "
            "locked before insertion."
        ),
    },
    {
        "name": "National Ambulance Service 102 — Assam",
        "emergency_type": "medical",
        "phone_number": "102",
        "jurisdiction": "Assam",
        "primary_source_name": (
            "National Health Mission Assam — National Ambulance Service 102"
        ),
        "primary_source_url": (
            "https://nhm.assam.gov.in/schemes/"
            "national-ambulances-services-%E2%80%9C102%E2%80%9D"
        ),
        "secondary_source_name": (
            "National Health Mission — ERS / Patient Transport Service"
        ),
        "secondary_source_url": (
            "https://www.nhm.gov.in/index1.php?"
            "lang=1&level=2&lid=189&sublinkid=1217"
        ),
        "verification_notes": (
            "Assam-specific source and national NHM source personally "
            "verified and locked. Assam record is retained separately "
            "for jurisdiction-aware routing."
        ),
    },
]


async def seed_emergency_contacts() -> None:
    async with AsyncSessionLocal() as db:
        inserted = 0
        updated = 0

        for contact_data in EMERGENCY_CONTACTS:
            statement = select(EmergencyContact).where(
                EmergencyContact.emergency_type
                == contact_data["emergency_type"],
                EmergencyContact.phone_number
                == contact_data["phone_number"],
                EmergencyContact.jurisdiction
                == contact_data["jurisdiction"],
            )

            result = await db.execute(statement)
            existing = result.scalar_one_or_none()

            if existing:
                existing.name = contact_data["name"]
                existing.primary_source_name = (
                    contact_data["primary_source_name"]
                )
                existing.primary_source_url = (
                    contact_data["primary_source_url"]
                )
                existing.secondary_source_name = (
                    contact_data["secondary_source_name"]
                )
                existing.secondary_source_url = (
                    contact_data["secondary_source_url"]
                )
                existing.is_verified = True
                existing.verified_at = datetime.now(timezone.utc)
                existing.verification_notes = (
                    contact_data["verification_notes"]
                )
                existing.is_active = True

                updated += 1

            else:
                contact = EmergencyContact(
                    **contact_data,
                    is_verified=True,
                    verified_at=datetime.now(timezone.utc),
                    is_active=True,
                )

                db.add(contact)
                inserted += 1

        await db.commit()

        print("Emergency contact seed completed.")
        print(f"Inserted: {inserted}")
        print(f"Updated: {updated}")
        print(f"Total seed records: {len(EMERGENCY_CONTACTS)}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_emergency_contacts())