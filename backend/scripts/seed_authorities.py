from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.authority import Authority
from app.models.jurisdiction import Jurisdiction


ASSAM_POLICE_AUTHORITY = {
    "name": "Assam Police",
    "authority_type": "police",
    "domain": "criminal",
    "service_key": "police_complaint",
    "service_name": "Police Complaint / e-FIR",
    "description": (
        "Official Assam Police authority for police complaints "
        "and supported e-FIR services through Assam Police Seva Setu."
    ),

    # We deliberately use only verified URLs.
    "official_portal_url": (
        "https://police.assam.gov.in/how-to/e-fir"
    ),
    "complaint_url": (
        "https://polcitizen.assam.gov.in/"
    ),

    # Not added until independently verified.
    "phone_number": None,
    "email": None,

    "primary_source_name": (
        "Assam Police — e-FIR"
    ),
    "primary_source_url": (
        "https://police.assam.gov.in/how-to/e-fir"
    ),

    "secondary_source_name": (
        "Assam Police — Seva Setu"
    ),
    "secondary_source_url": (
        "https://police.assam.gov.in/"
        "information-services/assam-police-seva-setu"
    ),

    "is_verified": True,
    "verification_notes": (
        "Primary and secondary Assam Police sources "
        "personally reviewed and explicitly locked "
        "for NyayaAI authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}


CYBERCRIME_AUTHORITY = {
    "name": "National Cyber Crime Reporting Portal",
    "authority_type": "cybercrime",
    "domain": "cybercrime",
    "service_key": "cybercrime_report",
    "service_name": "Cybercrime Reporting",
    "description": (
        "Official Government of India portal for reporting "
        "cybercrime complaints, including cyber financial fraud."
    ),

    "official_portal_url": (
        "https://www.cybercrime.gov.in/"
    ),
    "complaint_url": (
        "https://www.cybercrime.gov.in/"
    ),

    "phone_number": "1930",
    "email": None,

    "primary_source_name": (
        "National Cyber Crime Reporting Portal"
    ),
    "primary_source_url": (
        "https://www.cybercrime.gov.in/"
    ),

    "secondary_source_name": (
        "PIB / Ministry of Home Affairs — Cybercrime Reporting"
    ),
    "secondary_source_url": (
        "https://www.pib.gov.in/"
        "PressReleasePage.aspx?PRID=2290377&lang=1&reg=3"
    ),

    "is_verified": True,
    "verification_notes": (
        "Official National Cyber Crime Reporting Portal and "
        "PIB/MHA source personally reviewed and explicitly "
        "locked for NyayaAI authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}

CONSUMER_HELPLINE_AUTHORITY = {
    "name": "National Consumer Helpline",
    "authority_type": "consumer",
    "domain": "consumer",
    "service_key": "consumer_grievance",
    "service_name": "Consumer Grievance",
    "description": (
        "Official nationwide consumer grievance assistance "
        "service of the Department of Consumer Affairs."
    ),

    "official_portal_url": (
        "https://consumerhelpline.gov.in/"
    ),
    "complaint_url": (
        "https://consumerhelpline.gov.in/"
    ),

    "phone_number": "1915",
    "email": None,

    "primary_source_name": (
        "Department of Consumer Affairs — "
        "National Consumer Helpline"
    ),
    "primary_source_url": (
        "https://consumeraffairs.gov.in/pages/nch"
    ),

    "secondary_source_name": (
        "National Consumer Helpline — Official Portal"
    ),
    "secondary_source_url": (
        "https://consumerhelpline.gov.in/"
    ),

    "is_verified": True,
    "verification_notes": (
        "Department of Consumer Affairs and National "
        "Consumer Helpline official sources personally "
        "reviewed and explicitly locked for NyayaAI "
        "authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}

SAMADHAN_AUTHORITY = {
    "name": "SAMADHAN Portal",
    "authority_type": "labour",
    "domain": "employment",
    "service_key": "labour_grievance",
    "service_name": "Labour Grievance",
    "description": (
        "Official Ministry of Labour and Employment portal "
        "for labour grievances, industrial disputes, and "
        "eligible worker claims."
    ),

    "official_portal_url": (
        "https://samadhan.labour.gov.in/"
    ),
    "complaint_url": (
        "https://samadhan.labour.gov.in/"
    ),

    # No grievance phone/email stored until separately verified.
    "phone_number": None,
    "email": None,

    "primary_source_name": (
        "SAMADHAN Portal — Ministry of Labour "
        "and Employment"
    ),
    "primary_source_url": (
        "https://samadhan.labour.gov.in/"
    ),

    "secondary_source_name": (
        "PIB / Ministry of Labour and Employment — "
        "SAMADHAN Portal"
    ),
    "secondary_source_url": (
        "https://www.pib.gov.in/"
        "PressReleasePage.aspx?"
        "PRID=2146478&lang=2&reg=48"
    ),

    "is_verified": True,
    "verification_notes": (
        "Official SAMADHAN Portal and PIB / Ministry "
        "of Labour and Employment source personally "
        "reviewed and explicitly locked for NyayaAI "
        "authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}

SARATHI_AUTHORITY = {
    "name": "Sarathi Parivahan",
    "authority_type": "transport",
    "domain": "traffic",
    "service_key": "driving_licence_service",
    "service_name": "Driving Licence Services",
    "description": (
        "Official Parivahan service portal for driving "
        "licence and learner licence services."
    ),
    "official_portal_url": (
        "https://sarathi.parivahan.gov.in/"
        "sarathiservice/stateSelection.do"
    ),
    "complaint_url": None,
    "phone_number": None,
    "email": None,
    "primary_source_name": (
        "Sarathi Parivahan — Driving Licence Services"
    ),
    "primary_source_url": (
        "https://sarathi.parivahan.gov.in/"
        "sarathiservice/stateSelection.do"
    ),
    "secondary_source_name": None,
    "secondary_source_url": None,
    "is_verified": True,
    "verification_notes": (
        "Official Sarathi / Parivahan source personally "
        "reviewed and explicitly locked for NyayaAI "
        "authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}


VAHAN_AUTHORITY = {
    "name": "VAHAN 4.0 Citizen Services",
    "authority_type": "transport",
    "domain": "traffic",
    "service_key": "vehicle_registration_service",
    "service_name": "Vehicle Registration Services",
    "description": (
        "Official Parivahan vehicle services portal for "
        "vehicle registration and related citizen services."
    ),
    "official_portal_url": (
        "https://vahan.parivahan.gov.in/"
        "vahanservice/vahan/ui/statevalidation/homepage.xhtml"
    ),
    "complaint_url": None,
    "phone_number": None,
    "email": None,
    "primary_source_name": (
        "VAHAN 4.0 Citizen Services"
    ),
    "primary_source_url": (
        "https://vahan.parivahan.gov.in/"
        "vahanservice/vahan/ui/statevalidation/homepage.xhtml"
    ),
    "secondary_source_name": None,
    "secondary_source_url": None,
    "is_verified": True,
    "verification_notes": (
        "Official VAHAN / Parivahan source personally "
        "reviewed and explicitly locked for NyayaAI "
        "authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}


ECHALLAN_AUTHORITY = {
    "name": "eChallan Grievance System",
    "authority_type": "transport",
    "domain": "traffic",
    "service_key": "traffic_challan_service",
    "service_name": "Traffic Challan Grievance",
    "description": (
        "Official eChallan grievance service for raising "
        "eligible traffic challan complaints and grievances."
    ),
    "official_portal_url": (
        "https://echallan.parivahan.gov.in/gsticket/"
    ),
    "complaint_url": (
        "https://echallan.parivahan.gov.in/gsticket/"
    ),
    "phone_number": None,
    "email": None,
    "primary_source_name": (
        "eChallan — Grievance System"
    ),
    "primary_source_url": (
        "https://echallan.parivahan.gov.in/gsticket/"
    ),
    "secondary_source_name": None,
    "secondary_source_url": None,
    "is_verified": True,
    "verification_notes": (
        "Official eChallan / Parivahan grievance source "
        "personally reviewed and explicitly locked for "
        "NyayaAI authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}

MISSION_BASUNDHARA_AUTHORITY = {
    "name": "Mission Basundhara",
    "authority_type": "revenue_land",
    "domain": "property",
    "service_key": "property_land_service",
    "service_name": "Land and Revenue Services",
    "description": (
        "Official Government of Assam platform for land "
        "and revenue-related citizen services, including "
        "eligible mutation and land-record services."
    ),

    "official_portal_url": (
        "https://basundhara.assam.gov.in/"
    ),

    # This is a service portal, not a separately verified
    # grievance portal.
    "complaint_url": None,

    "phone_number": None,
    "email": None,

    "primary_source_name": (
        "Mission Basundhara — Government of Assam"
    ),
    "primary_source_url": (
        "https://basundhara.assam.gov.in/"
    ),

    "secondary_source_name": (
        "Integrated Land Records Management System "
        "(ILRMS) — Government of Assam"
    ),
    "secondary_source_url": (
        "https://ilrms.assam.gov.in/"
    ),

    "is_verified": True,
    "verification_notes": (
        "Official Mission Basundhara and Assam ILRMS "
        "sources personally reviewed and explicitly locked "
        "for NyayaAI authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}

ASLSA_AUTHORITY = {
    "name": "Assam State Legal Services Authority",
    "authority_type": "legal_services",
    "domain": "legal_services",
    "service_key": "legal_aid_service",
    "service_name": "Free Legal Aid",
    "description": (
        "Official Assam State Legal Services Authority "
        "service for eligible persons seeking free legal "
        "aid and legal services in Assam."
    ),

    "official_portal_url": (
        "https://assam.nalsa.gov.in/"
    ),

    # No separately verified complaint portal.
    "complaint_url": None,

    # Not stored until separately verified and locked.
    "phone_number": None,
    "email": None,

    "primary_source_name": (
        "Assam State Legal Services Authority — Legal Aid"
    ),
    "primary_source_url": (
        "https://assam.nalsa.gov.in/legal-aid/"
    ),

    "secondary_source_name": (
        "National Legal Services Authority — Legal Aid"
    ),
    "secondary_source_url": (
        "https://nalsa.gov.in/legal-aid/"
    ),

    "is_verified": True,
    "verification_notes": (
        "Official ASLSA and NALSA legal-aid sources "
        "personally reviewed and explicitly locked for "
        "NyayaAI authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}

ASSAM_EDISTRICT_AUTHORITY = {
    "name": "Assam e-District / Public Facilitation Centre",
    "authority_type": "district_administration",
    "domain": "government_services",
    "service_key": "district_administration_service",
    "service_name": "District Administration Services",
    "description": (
        "Official Government of Assam e-District and "
        "Public Facilitation Centre service for eligible "
        "district-level citizen services and certificates."
    ),

    "official_portal_url": (
        "https://sribhumi.assam.gov.in/"
        "information-and-services/"
        "edistrict-public-facilitation-centre"
    ),

    # We have not separately verified a complaint portal.
    "complaint_url": None,

    "phone_number": None,
    "email": None,

    "primary_source_name": (
        "Assam e-District / Public Facilitation Centre"
    ),
    "primary_source_url": (
        "https://sribhumi.assam.gov.in/"
        "information-and-services/"
        "edistrict-public-facilitation-centre"
    ),

    "secondary_source_name": (
        "Assam State Service Delivery Gateway — "
        "Income Certificate"
    ),
    "secondary_source_url": (
        "https://eforms.assam.gov.in/"
        "SPP/temp/INCOME%20CERTIFICATE.jsp"
    ),

    "is_verified": True,
    "verification_notes": (
        "Official Assam e-District / Public Facilitation "
        "Centre and Assam State Service Delivery Gateway "
        "sources personally reviewed and explicitly locked "
        "for NyayaAI authority ingestion."
    ),
    "is_active": True,
    "priority": 10,
}


async def get_assam_jurisdiction(
    session,
) -> Jurisdiction:
    """
    Resolve the existing Assam jurisdiction.

    The seed script must not silently create jurisdiction data.
    """

    result = await session.execute(
        select(Jurisdiction).where(
            Jurisdiction.code == "IN-AS",
            Jurisdiction.is_active.is_(True),
        )
    )

    jurisdiction = result.scalar_one_or_none()

    if jurisdiction is None:
        raise RuntimeError(
            "Active Assam jurisdiction with code 'IN-AS' "
            "was not found. Authority was not seeded."
        )

    return jurisdiction


async def get_india_jurisdiction(
    session,
) -> Jurisdiction:
    result = await session.execute(
        select(Jurisdiction).where(
            Jurisdiction.code == "IN",
            Jurisdiction.is_active.is_(True),
        )
    )

    jurisdiction = result.scalar_one_or_none()

    if jurisdiction is None:
        raise RuntimeError(
            "Active India jurisdiction with code 'IN' "
            "was not found. Authority was not seeded."
        )

    return jurisdiction

async def seed_samadhan_authority(
    session,
) -> None:
    jurisdiction = await get_india_jurisdiction(
        session
    )

    existing_result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id
            == jurisdiction.id,
            Authority.service_key
            == SAMADHAN_AUTHORITY["service_key"],
            Authority.name
            == SAMADHAN_AUTHORITY["name"],
        )
    )

    authority = existing_result.scalar_one_or_none()

    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **SAMADHAN_AUTHORITY,
        )

        session.add(authority)

        print(
            "CREATED: SAMADHAN Portal "
            "(labour_grievance / IN)"
        )

    else:
        for key, value in SAMADHAN_AUTHORITY.items():
            setattr(
                authority,
                key,
                value,
            )

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: SAMADHAN Portal "
            "(labour_grievance / IN)"
        )


async def seed_assam_police(
    session,
) -> None:
    """
    Insert or update the verified Assam Police authority.

    Idempotency key:
        jurisdiction_id
        + service_key
        + authority name
    """

    jurisdiction = await get_assam_jurisdiction(
        session
    )

    existing_result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id
            == jurisdiction.id,
            Authority.service_key
            == ASSAM_POLICE_AUTHORITY[
                "service_key"
            ],
            Authority.name
            == ASSAM_POLICE_AUTHORITY["name"],
        )
    )

    authority = (
        existing_result.scalar_one_or_none()
    )

    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **ASSAM_POLICE_AUTHORITY,
        )

        session.add(authority)

        print(
            "CREATED: Assam Police "
            "(police_complaint / AS)"
        )

    else:
        # Keep the existing row but synchronize it with
        # the currently locked verified source record.
        for key, value in (
            ASSAM_POLICE_AUTHORITY.items()
        ):
            setattr(
                authority,
                key,
                value,
            )

        authority.jurisdiction_id = (
            jurisdiction.id
        )

        authority.verified_at = verified_at

        print(
            "UPDATED: Assam Police "
            "(police_complaint / AS)"
        )


async def seed_cybercrime_authority(
    session,
) -> None:
    jurisdiction = await get_india_jurisdiction(
        session
    )

    existing_result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id
            == jurisdiction.id,
            Authority.service_key
            == CYBERCRIME_AUTHORITY["service_key"],
            Authority.name
            == CYBERCRIME_AUTHORITY["name"],
        )
    )

    authority = (
        existing_result.scalar_one_or_none()
    )

    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **CYBERCRIME_AUTHORITY,
        )

        session.add(authority)

        print(
            "CREATED: National Cyber Crime Reporting Portal "
            "(cybercrime_report / IN)"
        )

    else:
        for key, value in (
            CYBERCRIME_AUTHORITY.items()
        ):
            setattr(
                authority,
                key,
                value,
            )

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: National Cyber Crime Reporting Portal "
            "(cybercrime_report / IN)"
        )

async def seed_consumer_helpline(
    session,
) -> None:
    jurisdiction = await get_india_jurisdiction(
        session
    )

    existing_result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id
            == jurisdiction.id,
            Authority.service_key
            == CONSUMER_HELPLINE_AUTHORITY[
                "service_key"
            ],
            Authority.name
            == CONSUMER_HELPLINE_AUTHORITY["name"],
        )
    )

    authority = (
        existing_result.scalar_one_or_none()
    )

    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **CONSUMER_HELPLINE_AUTHORITY,
        )

        session.add(authority)

        print(
            "CREATED: National Consumer Helpline "
            "(consumer_grievance / IN)"
        )

    else:
        for key, value in (
            CONSUMER_HELPLINE_AUTHORITY.items()
        ):
            setattr(
                authority,
                key,
                value,
            )

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: National Consumer Helpline "
            "(consumer_grievance / IN)"
        )

async def seed_sarathi_authority(
    session,
) -> None:
    jurisdiction = await get_india_jurisdiction(session)

    result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id == jurisdiction.id,
            Authority.service_key
            == SARATHI_AUTHORITY["service_key"],
            Authority.name == SARATHI_AUTHORITY["name"],
        )
    )

    authority = result.scalar_one_or_none()
    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **SARATHI_AUTHORITY,
        )
        session.add(authority)

        print(
            "CREATED: Sarathi Parivahan "
            "(driving_licence_service / IN)"
        )

    else:
        for key, value in SARATHI_AUTHORITY.items():
            setattr(authority, key, value)

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: Sarathi Parivahan "
            "(driving_licence_service / IN)"
        )


async def seed_vahan_authority(
    session,
) -> None:
    jurisdiction = await get_india_jurisdiction(session)

    result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id == jurisdiction.id,
            Authority.service_key
            == VAHAN_AUTHORITY["service_key"],
            Authority.name == VAHAN_AUTHORITY["name"],
        )
    )

    authority = result.scalar_one_or_none()
    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **VAHAN_AUTHORITY,
        )
        session.add(authority)

        print(
            "CREATED: VAHAN 4.0 Citizen Services "
            "(vehicle_registration_service / IN)"
        )

    else:
        for key, value in VAHAN_AUTHORITY.items():
            setattr(authority, key, value)

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: VAHAN 4.0 Citizen Services "
            "(vehicle_registration_service / IN)"
        )


async def seed_echallan_authority(
    session,
) -> None:
    jurisdiction = await get_india_jurisdiction(session)

    result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id == jurisdiction.id,
            Authority.service_key
            == ECHALLAN_AUTHORITY["service_key"],
            Authority.name == ECHALLAN_AUTHORITY["name"],
        )
    )

    authority = result.scalar_one_or_none()
    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **ECHALLAN_AUTHORITY,
        )
        session.add(authority)

        print(
            "CREATED: eChallan Grievance System "
            "(traffic_challan_service / IN)"
        )

    else:
        for key, value in ECHALLAN_AUTHORITY.items():
            setattr(authority, key, value)

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: eChallan Grievance System "
            "(traffic_challan_service / IN)"
        )

async def seed_mission_basundhara(
    session,
) -> None:
    jurisdiction = await get_assam_jurisdiction(
        session
    )

    result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id
            == jurisdiction.id,
            Authority.service_key
            == MISSION_BASUNDHARA_AUTHORITY[
                "service_key"
            ],
            Authority.name
            == MISSION_BASUNDHARA_AUTHORITY["name"],
        )
    )

    authority = result.scalar_one_or_none()
    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **MISSION_BASUNDHARA_AUTHORITY,
        )

        session.add(authority)

        print(
            "CREATED: Mission Basundhara "
            "(property_land_service / IN-AS)"
        )

    else:
        for key, value in (
            MISSION_BASUNDHARA_AUTHORITY.items()
        ):
            setattr(
                authority,
                key,
                value,
            )

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: Mission Basundhara "
            "(property_land_service / IN-AS)"
        )

async def seed_aslsa_authority(
    session,
) -> None:
    jurisdiction = await get_assam_jurisdiction(
        session
    )

    result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id
            == jurisdiction.id,
            Authority.service_key
            == ASLSA_AUTHORITY["service_key"],
            Authority.name
            == ASLSA_AUTHORITY["name"],
        )
    )

    authority = result.scalar_one_or_none()
    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **ASLSA_AUTHORITY,
        )

        session.add(authority)

        print(
            "CREATED: Assam State Legal Services Authority "
            "(legal_aid_service / IN-AS)"
        )

    else:
        for key, value in ASLSA_AUTHORITY.items():
            setattr(
                authority,
                key,
                value,
            )

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: Assam State Legal Services Authority "
            "(legal_aid_service / IN-AS)"
        )

async def seed_assam_edistrict(
    session,
) -> None:
    jurisdiction = await get_assam_jurisdiction(
        session
    )

    result = await session.execute(
        select(Authority).where(
            Authority.jurisdiction_id
            == jurisdiction.id,
            Authority.service_key
            == ASSAM_EDISTRICT_AUTHORITY[
                "service_key"
            ],
            Authority.name
            == ASSAM_EDISTRICT_AUTHORITY["name"],
        )
    )

    authority = result.scalar_one_or_none()
    verified_at = datetime.now(timezone.utc)

    if authority is None:
        authority = Authority(
            jurisdiction_id=jurisdiction.id,
            verified_at=verified_at,
            **ASSAM_EDISTRICT_AUTHORITY,
        )

        session.add(authority)

        print(
            "CREATED: Assam e-District / "
            "Public Facilitation Centre "
            "(district_administration_service / IN-AS)"
        )

    else:
        for key, value in (
            ASSAM_EDISTRICT_AUTHORITY.items()
        ):
            setattr(
                authority,
                key,
                value,
            )

        authority.jurisdiction_id = jurisdiction.id
        authority.verified_at = verified_at

        print(
            "UPDATED: Assam e-District / "
            "Public Facilitation Centre "
            "(district_administration_service / IN-AS)"
        )


async def main() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await seed_assam_police(session)
            await seed_cybercrime_authority(session)
            await seed_consumer_helpline(session)
            await seed_samadhan_authority(session)
            await seed_sarathi_authority(session)
            await seed_vahan_authority(session)
            await seed_echallan_authority(session)
            await seed_mission_basundhara(session)
            await seed_aslsa_authority(session)
            await seed_assam_edistrict(session)


            await session.commit()

            print(
                "Authority seed completed successfully."
            )

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
