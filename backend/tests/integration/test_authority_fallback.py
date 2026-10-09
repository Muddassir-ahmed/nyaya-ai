from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.authority import Authority
from app.models.jurisdiction import Jurisdiction
from app.services.authority_orchestrator import (
    AuthorityOrchestrator,
)
from app.services.query_orchestrator import (
    QueryOrchestrator,
)


async def get_or_create_jurisdictions(db):
    india_result = await db.execute(
        select(Jurisdiction).where(
            Jurisdiction.code == "IN"
        )
    )

    india = india_result.scalar_one_or_none()

    if india is None:
        india = Jurisdiction(
            name="India",
            code="IN",
            type="country",
            parent_id=None,
            country_code="IN",
            is_active=True,
        )

        db.add(india)
        await db.flush()

    assam_result = await db.execute(
        select(Jurisdiction).where(
            Jurisdiction.code == "IN-AS"
        )
    )

    assam = assam_result.scalar_one_or_none()

    if assam is None:
        assam = Jurisdiction(
            name="Assam",
            code="IN-AS",
            type="state",
            parent_id=india.id,
            country_code="IN",
            is_active=True,
        )

        db.add(assam)
        await db.flush()

    return india, assam


@pytest.mark.asyncio
async def test_assam_cybercrime_falls_back_to_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    authority = Authority(
        name="Test National Cybercrime Portal",
        authority_type="cybercrime",
        domain="cybercrime",
        service_key="cybercrime_report",
        service_name="Cybercrime Reporting",
        description=(
            "Synthetic national cybercrime authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com",
        complaint_url="https://example.com/report",
        phone_number="1930",
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url=(
            "https://example.com/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add(authority)
    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Where should I report a phishing scam "
            "in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    # User requested Assam.
    assert response.jurisdiction == "IN-AS"

    # Cybercrime service was detected.
    assert response.service_key == "cybercrime_report"

    # No Assam-specific record exists, so the directory
    # must climb IN-AS -> IN.
    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert (
        returned_authority.name
        == "Test National Cybercrime Portal"
    )

    assert returned_authority.jurisdiction_code == "IN"
    assert returned_authority.is_verified is True
    assert returned_authority.phone_number == "1930"

    # Authority lookups must never enter legal RAG/LLM.
    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_consumer_grievance_falls_back_to_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    authority = Authority(
        name="Test National Consumer Helpline",
        authority_type="consumer",
        domain="consumer",
        service_key="consumer_grievance",
        service_name="Consumer Grievance",
        description=(
            "Synthetic national consumer authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com",
        complaint_url="https://example.com/complaint",
        phone_number="1915",
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url="https://example.com/source",
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add(authority)
    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Where should I complain about a defective "
            "product refund in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert response.service_key == "consumer_grievance"

    # Requested jurisdiction remains Assam.
    assert response.jurisdiction == "IN-AS"

    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    # Authority came from parent India jurisdiction.
    assert returned_authority.jurisdiction_code == "IN"

    assert (
        returned_authority.name
        == "Test National Consumer Helpline"
    )

    assert returned_authority.phone_number == "1915"
    assert returned_authority.is_verified is True

    # Authority routing must never enter legal RAG/LLM.
    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_labour_grievance_falls_back_to_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    authority = Authority(
        name="Test National Labour Grievance Portal",
        authority_type="labour",
        domain="employment",
        service_key="labour_grievance",
        service_name="Labour Grievance",
        description=(
            "Synthetic national labour authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com",
        complaint_url="https://example.com/complaint",
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url="https://example.com/source",
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add(authority)
    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Which department should I contact about "
            "unpaid salary in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert response.service_key == "labour_grievance"
    assert response.jurisdiction == "IN-AS"

    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert returned_authority.jurisdiction_code == "IN"

    assert (
        returned_authority.name
        == "Test National Labour Grievance Portal"
    )

    assert returned_authority.is_verified is True
    assert returned_authority.phone_number is None
    assert returned_authority.email is None

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_driving_licence_falls_back_to_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    authority = Authority(
        name="Test Sarathi Parivahan",
        authority_type="transport",
        domain="traffic",
        service_key="driving_licence_service",
        service_name="Driving Licence Services",
        description=(
            "Synthetic national driving licence authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url="https://example.com/source",
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add(authority)
    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Which authority should I contact to renew "
            "my driving licence in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert (
        response.service_key
        == "driving_licence_service"
    )

    assert response.jurisdiction == "IN-AS"
    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert returned_authority.jurisdiction_code == "IN"

    assert (
        returned_authority.name
        == "Test Sarathi Parivahan"
    )

    assert returned_authority.is_verified is True

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_vehicle_registration_falls_back_to_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    authority = Authority(
        name="Test VAHAN Citizen Services",
        authority_type="transport",
        domain="traffic",
        service_key="vehicle_registration_service",
        service_name="Vehicle Registration Services",
        description=(
            "Synthetic national vehicle registration authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url="https://example.com/source",
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add(authority)
    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Which department handles vehicle "
            "registration in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert (
        response.service_key
        == "vehicle_registration_service"
    )

    assert response.jurisdiction == "IN-AS"
    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert returned_authority.jurisdiction_code == "IN"

    assert (
        returned_authority.name
        == "Test VAHAN Citizen Services"
    )

    assert returned_authority.is_verified is True

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_traffic_challan_falls_back_to_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    authority = Authority(
        name="Test eChallan Grievance System",
        authority_type="transport",
        domain="traffic",
        service_key="traffic_challan_service",
        service_name="Traffic Challan Grievance",
        description=(
            "Synthetic national traffic challan authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com",
        complaint_url="https://example.com/grievance",
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url="https://example.com/source",
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add(authority)
    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Where should I report an incorrect "
            "traffic challan in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert (
        response.service_key
        == "traffic_challan_service"
    )

    assert response.jurisdiction == "IN-AS"
    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert returned_authority.jurisdiction_code == "IN"

    assert (
        returned_authority.name
        == "Test eChallan Grievance System"
    )

    assert returned_authority.is_verified is True

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_property_authority_preferred_over_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    national_authority = Authority(
        name="Test National Land Authority",
        authority_type="revenue_land",
        domain="property",
        service_key="property_land_service",
        service_name="National Land Service",
        description=(
            "Synthetic national property authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com/india",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url=(
            "https://example.com/india/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    assam_authority = Authority(
        name="Test Mission Basundhara",
        authority_type="revenue_land",
        domain="property",
        service_key="property_land_service",
        service_name="Land and Revenue Services",
        description=(
            "Synthetic Assam property authority "
            "used only for automated testing."
        ),
        jurisdiction_id=assam.id,
        official_portal_url="https://example.com/assam",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Assam Government Source",
        primary_source_url=(
            "https://example.com/assam/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add_all(
        [
            national_authority,
            assam_authority,
        ]
    )

    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Which authority should I contact for "
            "land mutation in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert (
        response.service_key
        == "property_land_service"
    )

    assert response.jurisdiction == "IN-AS"

    # The Assam authority must win.
    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert (
        returned_authority.name
        == "Test Mission Basundhara"
    )

    assert (
        returned_authority.jurisdiction_code
        == "IN-AS"
    )

    assert returned_authority.is_verified is True

    # National fallback must NOT be returned when a valid
    # state-specific authority already exists.
    assert all(
        authority.name != "Test National Land Authority"
        for authority in response.authorities
    )

    # Authority routing bypasses legal RAG / LLM.
    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_legal_aid_preferred_over_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    national_authority = Authority(
        name="Test National Legal Aid Authority",
        authority_type="legal_services",
        domain="legal_services",
        service_key="legal_aid_service",
        service_name="National Legal Aid",
        description=(
            "Synthetic national legal-aid authority "
            "used only for automated testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com/india",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url=(
            "https://example.com/india/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    assam_authority = Authority(
        name="Test Assam Legal Services Authority",
        authority_type="legal_services",
        domain="legal_services",
        service_key="legal_aid_service",
        service_name="Free Legal Aid",
        description=(
            "Synthetic Assam legal-aid authority "
            "used only for automated testing."
        ),
        jurisdiction_id=assam.id,
        official_portal_url="https://example.com/assam",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Assam Government Source",
        primary_source_url=(
            "https://example.com/assam/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add_all(
        [
            national_authority,
            assam_authority,
        ]
    )

    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Where can I get free legal aid in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert response.service_key == "legal_aid_service"
    assert response.jurisdiction == "IN-AS"

    # Assam-specific authority must win.
    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert (
        returned_authority.name
        == "Test Assam Legal Services Authority"
    )

    assert (
        returned_authority.jurisdiction_code
        == "IN-AS"
    )

    assert returned_authority.is_verified is True

    # National fallback must not be returned when a
    # verified Assam-specific authority exists.
    assert all(
        authority.name
        != "Test National Legal Aid Authority"
        for authority in response.authorities
    )

    # Authority routing must bypass legal RAG / LLM.
    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_assam_district_administration_preferred_over_india(
    db_session,
):
    india, assam = await get_or_create_jurisdictions(
        db_session
    )

    assert assam.parent_id == india.id

    national_authority = Authority(
        name="Test National District Service",
        authority_type="district_administration",
        domain="government_services",
        service_key="district_administration_service",
        service_name="National District Service",
        description=(
            "Synthetic national district administration "
            "authority used only for testing."
        ),
        jurisdiction_id=india.id,
        official_portal_url="https://example.com/india",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url=(
            "https://example.com/india/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    assam_authority = Authority(
        name="Test Assam e-District",
        authority_type="district_administration",
        domain="government_services",
        service_key="district_administration_service",
        service_name="District Administration Services",
        description=(
            "Synthetic Assam district administration "
            "authority used only for testing."
        ),
        jurisdiction_id=assam.id,
        official_portal_url="https://example.com/assam",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Assam Government Source",
        primary_source_url=(
            "https://example.com/assam/source"
        ),
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        is_active=True,
        priority=10,
    )

    db_session.add_all(
        [
            national_authority,
            assam_authority,
        ]
    )

    await db_session.commit()

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=AuthorityOrchestrator(),
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=db_session,
        query=(
            "Which office should I contact for a "
            "residence certificate in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.retrieval_performed is False
    assert result.legal_answer is None

    assert result.authority_response is not None

    response = result.authority_response

    assert (
        response.service_key
        == "district_administration_service"
    )

    assert response.jurisdiction == "IN-AS"

    assert len(response.authorities) == 1

    returned_authority = response.authorities[0]

    assert (
        returned_authority.name
        == "Test Assam e-District"
    )

    assert (
        returned_authority.jurisdiction_code
        == "IN-AS"
    )

    assert returned_authority.is_verified is True

    # National fallback must not be returned because
    # a verified Assam-specific authority exists.
    assert all(
        authority.name
        != "Test National District Service"
        for authority in response.authorities
    )

    # Civic authority lookup must bypass legal RAG / LLM.
    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()
