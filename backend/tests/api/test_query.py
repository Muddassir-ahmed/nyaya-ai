from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.citation_validation import CitationValidationResult
from app.schemas.claim_validation import (
    ClaimSupportLevel,
    ClaimValidation,
    ClaimValidationResult,
)
from app.schemas.answer_integrity import (
    AnswerIntegrityIssue,
    AnswerIntegrityResult,
)
from app.schemas.emergency import (
    EmergencyResponse,
    EmergencyType,
)
from app.schemas.authority import (
    AuthorityRecord,
    AuthorityResponse,
    AuthorityType,
)
from app.schemas.legal_answer import LegalAnswer
from app.services.query_analyzer import QueryAnalyzer
from app.services.query_orchestrator import (
    QueryOrchestrationResult,
    get_query_orchestrator,
)


class FakeQueryOrchestrator:
    def __init__(
        self,
        result: QueryOrchestrationResult,
    ):
        self.handle = AsyncMock(
            return_value=result
        )


@pytest.mark.asyncio
async def test_query_api_returns_emergency_route(
    db_session,
):
    analysis = QueryAnalyzer().analyze(
        "Someone is attacking me right now"
    )

    emergency_response = EmergencyResponse(
        is_emergency=True,
        emergency_type=EmergencyType.POLICE,
        immediate_actions=[
            "Move to a safer location if possible."
        ],
        contacts=[],
        safety_warning="Test safety warning.",
        verification_note="Test verification note.",
    )

    result = QueryOrchestrationResult(
        route="emergency",
        analysis=analysis,
        emergency_response=emergency_response,
        retrieval_performed=False,
        routing_reason=(
            "Emergency query routed to the "
            "verified safety/emergency pipeline."
        ),
    )

    fake_orchestrator = FakeQueryOrchestrator(
        result
    )

    app.dependency_overrides[
        get_query_orchestrator
    ] = lambda: fake_orchestrator

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={
                    "query": (
                        "Someone is attacking me right now"
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == "emergency"
    assert data["emergency_response"] is not None
    assert (
        data["emergency_response"]["emergency_type"]
        == "police"
    )
    assert data["legal_answer"] is None
    assert data["retrieval_performed"] is False


@pytest.mark.asyncio
async def test_query_api_returns_legal_route(
    db_session,
):
    analysis = QueryAnalyzer().analyze(
        "What is theft?"
    )

    legal_answer = LegalAnswer(
        summary="Test grounded legal answer.",
        legal_basis=[
            "Test supported legal basis."
        ],
        citations=["E1"],
    )

    result = QueryOrchestrationResult(
        route="legal",
        analysis=analysis,
        legal_answer=legal_answer,
        retrieval_performed=True,
    )

    fake_orchestrator = FakeQueryOrchestrator(
        result
    )

    app.dependency_overrides[
        get_query_orchestrator
    ] = lambda: fake_orchestrator

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={
                    "query": "What is theft?",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == "legal"
    assert data["legal_answer"] is not None

    assert (
        data["legal_answer"]["summary"]
        == "Test grounded legal answer."
    )

    assert data["emergency_response"] is None
    assert data["retrieval_performed"] is True


@pytest.mark.asyncio
async def test_query_api_passes_explicit_jurisdiction(
    db_session,
):
    analysis = QueryAnalyzer().analyze(
        "Someone is unconscious"
    )

    emergency_response = EmergencyResponse(
        is_emergency=True,
        emergency_type=EmergencyType.MEDICAL,
        immediate_actions=[],
        contacts=[],
        safety_warning="Test warning.",
        verification_note="Verified test contact data.",
    )

    result = QueryOrchestrationResult(
        route="emergency",
        analysis=analysis,
        emergency_response=emergency_response,
        retrieval_performed=False,
    )

    fake_orchestrator = FakeQueryOrchestrator(
        result
    )

    app.dependency_overrides[
        get_query_orchestrator
    ] = lambda: fake_orchestrator

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={
                    "query": "Someone is unconscious",
                    "jurisdiction": "Assam",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    fake_orchestrator.handle.assert_awaited_once()

    called_kwargs = (
        fake_orchestrator.handle.await_args.kwargs
    )

    assert called_kwargs["query"] == (
        "Someone is unconscious"
    )

    assert called_kwargs["jurisdiction"] == "Assam"


@pytest.mark.asyncio
async def test_query_api_rejects_empty_query(
    db_session,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/query",
            json={
                "query": "",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_api_rejects_whitespace_query(
    db_session,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/query",
            json={
                "query": "     ",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_api_rejects_missing_query(
    db_session,
):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/query",
            json={},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_api_does_not_expose_blocked_claim_text(
    db_session,
):
    analysis = QueryAnalyzer().analyze(
        "What is theft?"
    )

    blocked_claim = (
        "Every theft offence automatically results "
        "in ten years of imprisonment."
    )

    legal_answer = LegalAnswer(
        summary=(
            "I cannot safely provide the generated legal "
            "answer because it did not pass NyayaAI's "
            "evidence-grounding checks."
        ),
        caveats=[
            "The generated response was blocked."
        ],
        citations=[],
    )

    citation_validation = CitationValidationResult(
        is_valid=True,
        citation_completeness=1.0,
        valid_citations=["E1"],
        invalid_citations=[],
        validation_reasons=[
            "All generated citation IDs match verified evidence."
        ],
    )

    claim_validation = ClaimValidationResult(
        is_valid=False,
        claims=[
            ClaimValidation(
                claim=blocked_claim,
                citation_ids=["E1"],
                support_level=ClaimSupportLevel.UNSUPPORTED,
                reason=(
                    "Claim has insufficient lexical overlap "
                    "with the cited legal evidence."
                ),
            )
        ],
        unsupported_claims=[blocked_claim],
        validation_reasons=[
            "Claim has insufficient lexical overlap."
        ],
    )

    result = QueryOrchestrationResult(
        route="legal",
        analysis=analysis,
        legal_answer=legal_answer,
        citation_validation=citation_validation,
        claim_validation=claim_validation,
        retrieval_performed=True,
        answer_blocked=True,
        safety_reason=(
            "one or more generated legal claims were not "
            "sufficiently supported by verified evidence"
        ),
    )

    fake_orchestrator = FakeQueryOrchestrator(
        result
    )

    app.dependency_overrides[
        get_query_orchestrator
    ] = lambda: fake_orchestrator

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={
                    "query": "What is theft?",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["answer_blocked"] is True

    assert data["validation"]["citation_valid"] is True
    assert (
        data["validation"]["claim_grounding_valid"]
        is False
    )

    # Critical security/safety assertion:
    assert blocked_claim not in response.text

    # Internal validation objects must not be publicly exposed.
    assert "unsupported_claims" not in data
    assert "claim_validation" not in data
    assert "citation_validation" not in data

@pytest.mark.asyncio
async def test_query_api_exposes_integrity_status_without_internal_details(
    db_session,
):
    analysis = QueryAnalyzer().analyze(
        "What is the punishment for theft?"
    )

    internal_claim = (
        "Internal generated legal rule that failed "
        "answer-integrity validation."
    )

    legal_answer = LegalAnswer(
        summary=(
            "I cannot safely provide the generated legal "
            "answer because it did not pass NyayaAI's "
            "evidence-grounding checks."
        ),
        caveats=[
            "The generated response was blocked."
        ],
        citations=[],
    )

    citation_validation = CitationValidationResult(
        is_valid=True,
        citation_completeness=1.0,
        valid_citations=["E1"],
        invalid_citations=[],
        validation_reasons=[
            "All generated citation IDs match verified evidence."
        ],
    )

    claim_validation = ClaimValidationResult(
        is_valid=True,
        claims=[],
        supported_claims=[],
        partially_supported_claims=[],
        unsupported_claims=[],
        validation_reasons=[],
    )

    answer_integrity = AnswerIntegrityResult(
        is_valid=False,
        issues=[
            AnswerIntegrityIssue(
                code="omitted_qualified_rule",
                message=(
                    "A material qualified legal rule "
                    "was omitted."
                ),
                claim=internal_claim,
                citation_id="E1",
            )
        ],
    )

    result = QueryOrchestrationResult(
        route="legal",
        analysis=analysis,
        legal_answer=legal_answer,
        citation_validation=citation_validation,
        claim_validation=claim_validation,
        answer_integrity=answer_integrity,
        retrieval_performed=True,
        answer_blocked=True,
        safety_reason=(
            "the generated legal answer failed "
            "answer-integrity checks"
        ),
    )

    fake_orchestrator = FakeQueryOrchestrator(
        result
    )

    app.dependency_overrides[
        get_query_orchestrator
    ] = lambda: fake_orchestrator

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={
                    "query": (
                        "What is the punishment for theft?"
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["answer_blocked"] is True

    assert data["validation"]["citation_valid"] is True

    assert (
        data["validation"]["claim_grounding_valid"]
        is True
    )

    assert (
        data["validation"]["answer_integrity_valid"]
        is False
    )

    # Internal integrity details must remain private.
    assert internal_claim not in response.text

    assert "answer_integrity" not in data
    assert "issues" not in data

@pytest.mark.asyncio
async def test_query_api_returns_follow_up_route(
    db_session,
):
    analysis = QueryAnalyzer().analyze(
        "Where should I report my stolen bike?"
    )

    result = QueryOrchestrationResult(
        route="follow_up",
        analysis=analysis,
        retrieval_performed=False,
        routing_reason=(
            "Additional jurisdiction information "
            "is required."
        ),
        follow_up_question=(
            "Which Indian state or union territory "
            "is this situation in?"
        ),
    )

    fake_orchestrator = FakeQueryOrchestrator(
        result
    )

    app.dependency_overrides[
        get_query_orchestrator
    ] = lambda: fake_orchestrator

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={
                    "query": (
                        "Where should I report "
                        "my stolen bike?"
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == "follow_up"
    assert data["retrieval_performed"] is False
    assert data["follow_up_question"] is not None

    assert "state or union territory" in (
        data["follow_up_question"].lower()
    )

@pytest.mark.asyncio
async def test_query_api_returns_authority_response(
    db_session,
):
    analysis = QueryAnalyzer().analyze(
        "Where should I report my stolen bike in Assam?"
    )

    authority = AuthorityRecord(
        id=1,
        name="Test Assam Police",
        authority_type=AuthorityType.POLICE,
        domain="criminal",
        service_key="police_complaint",
        service_name="Police complaint",
        description="Test authority.",
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

    authority_response = AuthorityResponse(
        service_key="police_complaint",
        jurisdiction="AS",
        authorities=[authority],
        verification_note=(
            "Authority information was retrieved "
            "from verified structured records."
        ),
    )

    result = QueryOrchestrationResult(
        route="authority",
        analysis=analysis,
        authority_response=authority_response,
        retrieval_performed=False,
        routing_reason=(
            "Authority lookup routed to the verified "
            "structured authority directory."
        ),
    )

    fake_orchestrator = FakeQueryOrchestrator(
        result
    )

    app.dependency_overrides[
        get_query_orchestrator
    ] = lambda: fake_orchestrator

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/query",
                json={
                    "query": (
                        "Where should I report my "
                        "stolen bike in Assam?"
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["route"] == "authority"
    assert data["authority_response"] is not None

    assert (
        data["authority_response"]["service_key"]
        == "police_complaint"
    )

    assert len(
        data["authority_response"]["authorities"]
    ) == 1

    assert (
        data["authority_response"]["authorities"][0]["name"]
        == "Test Assam Police"
    )

    assert data["legal_answer"] is None
    assert data["emergency_response"] is None
