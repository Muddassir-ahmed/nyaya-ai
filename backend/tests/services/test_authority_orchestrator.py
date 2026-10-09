from unittest.mock import AsyncMock

import pytest

from app.schemas.authority import (
    AuthorityRecord,
    AuthorityType,
)
from app.services.authority_orchestrator import (
    AuthorityOrchestrator,
)
from app.services.query_analyzer import QueryAnalyzer


def build_test_authority(
    *,
    service_key: str,
) -> AuthorityRecord:
    return AuthorityRecord(
        id=1,
        name="Test Government Authority",
        authority_type=AuthorityType.POLICE,
        domain="criminal",
        service_key=service_key,
        service_name="Test Service",
        description="Test verified authority.",
        jurisdiction_id=1,
        jurisdiction_name="Assam",
        jurisdiction_code="AS",
        official_portal_url="https://example.com",
        complaint_url=None,
        phone_number=None,
        email=None,
        primary_source_name="Test Government Source",
        primary_source_url="https://example.com/source",
        secondary_source_name=None,
        secondary_source_url=None,
        is_verified=True,
        verified_at=None,
        verification_notes="Test only.",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_stolen_property_routes_to_police_complaint():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = [
        build_test_authority(
            service_key="police_complaint"
        )
    ]

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Where should I report my stolen bike "
            "in Assam?"
        ),
    )

    assert response.service_key == "police_complaint"
    assert response.jurisdiction == "IN-AS"
    assert len(response.authorities) == 1

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="police_complaint",
        jurisdiction="IN-AS",
    )


@pytest.mark.asyncio
async def test_phishing_routes_to_cybercrime_report():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Which authority should I report a "
            "phishing scam to in Assam?"
        ),
    )

    assert response.service_key == "cybercrime_report"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="cybercrime_report",
        jurisdiction="IN-AS",
    )


@pytest.mark.asyncio
async def test_consumer_issue_routes_to_consumer_grievance():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Which authority handles a defective "
            "product refund in Assam?"
        ),
    )

    assert response.service_key == "consumer_grievance"


@pytest.mark.asyncio
async def test_salary_issue_routes_to_labour_grievance():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Which department should I contact about "
            "unpaid salary in Assam?"
        ),
    )

    assert response.service_key == "labour_grievance"


@pytest.mark.asyncio
async def test_challan_issue_routes_to_traffic_challan_service():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Where should I report an incorrect "
            "traffic challan in Assam?"
        ),
    )

    assert response.service_key == "traffic_challan_service"
    assert response.jurisdiction == "IN-AS"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="traffic_challan_service",
        jurisdiction="IN-AS",
    )


@pytest.mark.asyncio
async def test_explicit_jurisdiction_overrides_detected_jurisdiction():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Where should I report theft in Assam?"
        ),
        jurisdiction="Karnataka",
    )

    assert response.jurisdiction == "Karnataka"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="police_complaint",
        jurisdiction="Karnataka",
    )


@pytest.mark.asyncio
async def test_missing_jurisdiction_does_not_query_directory():
    authority_service = AsyncMock()

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    analysis = QueryAnalyzer().analyze(
        "Where should I report my stolen bike?"
    )

    response = await orchestrator.handle(
        db=None,
        query="Where should I report my stolen bike?",
        analysis=analysis,
    )

    assert response.service_key == "police_complaint"
    assert response.jurisdiction is None
    assert response.authorities == []

    assert response.verification_note is not None

    authority_service.get_verified_authorities.assert_not_awaited()

@pytest.mark.asyncio
async def test_driving_licence_routes_to_driving_licence_service():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Which authority should I contact to renew "
            "my driving licence in Assam?"
        ),
    )

    assert response.service_key == "driving_licence_service"
    assert response.jurisdiction == "IN-AS"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="driving_licence_service",
        jurisdiction="IN-AS",
    )

@pytest.mark.asyncio
async def test_vehicle_registration_routes_to_vehicle_registration_service():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Which department handles vehicle "
            "registration in Assam?"
        ),
    )

    assert (
        response.service_key
        == "vehicle_registration_service"
    )

    assert response.jurisdiction == "IN-AS"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="vehicle_registration_service",
        jurisdiction="IN-AS",
    )

@pytest.mark.asyncio
async def test_generic_rto_query_routes_to_transport_service():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Which RTO should I contact in Assam?"
        ),
    )

    assert response.service_key == "transport_service"
    assert response.jurisdiction == "IN-AS"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="transport_service",
        jurisdiction="IN-AS",
    )

@pytest.mark.asyncio
async def test_legal_aid_routes_to_legal_aid_service():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query="Where can I get free legal aid in Assam?",
    )

    assert response.service_key == "legal_aid_service"
    assert response.jurisdiction == "IN-AS"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="legal_aid_service",
        jurisdiction="IN-AS",
    )

@pytest.mark.asyncio
async def test_residence_certificate_routes_to_district_administration_service():
    authority_service = AsyncMock()

    authority_service.get_verified_authorities.return_value = []

    orchestrator = AuthorityOrchestrator(
        authority_service=authority_service,
    )

    response = await orchestrator.handle(
        db=None,
        query=(
            "Which office should I contact for a "
            "residence certificate in Assam?"
        ),
    )

    assert (
        response.service_key
        == "district_administration_service"
    )

    assert response.jurisdiction == "IN-AS"

    authority_service.get_verified_authorities.assert_awaited_once_with(
        db=None,
        service_key="district_administration_service",
        jurisdiction="IN-AS",
    )
