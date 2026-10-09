from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.authority import AuthorityResponse
from app.schemas.emergency import (
    EmergencyResponse,
    EmergencyType,
)
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.schemas.query_analysis import LegalIntent
from app.services.query_orchestrator import (
    QueryOrchestrator,
)


@pytest.mark.asyncio
async def test_emergency_short_circuits_legal_retrieval():
    emergency_orchestrator = AsyncMock()

    emergency_orchestrator.handle.return_value = (
        EmergencyResponse(
            is_emergency=True,
            emergency_type=EmergencyType.POLICE,
            immediate_actions=[],
            contacts=[],
            safety_warning="Test warning",
            verification_note="Test verification",
        )
    )

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        emergency_orchestrator=emergency_orchestrator,
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query=(
            "Someone is threatening to kill me right now "
            "and is standing outside my home."
        ),
    )

    assert result.route == "emergency"
    assert result.emergency_response is not None
    assert result.emergency_response.is_emergency is True

    emergency_orchestrator.handle.assert_awaited_once()

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_jurisdiction_returns_follow_up_without_rag():
    authority_orchestrator = AsyncMock()
    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=authority_orchestrator,
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query="Where should I report my stolen bike?",
    )

    assert result.route == "follow_up"
    assert result.retrieval_performed is False

    assert result.follow_up_question is not None
    assert "state or union territory" in (
        result.follow_up_question.lower()
    )

    assert (
        "state_or_jurisdiction"
        in result.analysis.missing_information
    )

    authority_orchestrator.handle.assert_not_awaited()

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_authority_query_with_jurisdiction_routes_authority():
    authority_orchestrator = AsyncMock()

    authority_orchestrator.handle.return_value = AuthorityResponse(
        service_key="police_complaint",
        jurisdiction="AS",
        authorities=[],
        verification_note="Test authority response.",
    )

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=authority_orchestrator,
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query=(
            "Where should I report my stolen bike "
            "in Assam?"
        ),
    )

    assert result.route == "authority"
    assert result.analysis.jurisdiction == "AS"
    assert result.analysis.requires_follow_up is False
    assert result.retrieval_performed is False

    assert result.authority_response is not None

    assert (
        result.authority_response.service_key
        == "police_complaint"
    )

    authority_orchestrator.handle.assert_awaited_once_with(
        db=None,
        query=(
            "Where should I report my stolen bike "
            "in Assam?"
        ),
        jurisdiction=None,
        analysis=result.analysis,
    )

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_jurisdiction_satisfies_authority_follow_up():
    authority_orchestrator = AsyncMock()

    authority_orchestrator.handle.return_value = AuthorityResponse(
        service_key="police_complaint",
        jurisdiction="Assam",
        authorities=[],
        verification_note="Test authority response.",
    )

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        authority_orchestrator=authority_orchestrator,
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query="Where should I report my stolen bike?",
        jurisdiction="Assam",
    )

    assert result.route == "authority"
    assert result.analysis.jurisdiction == "Assam"
    assert result.analysis.requires_follow_up is False

    assert (
        "state_or_jurisdiction"
        not in result.analysis.missing_information
    )

    assert result.authority_response is not None

    authority_orchestrator.handle.assert_awaited_once_with(
        db=None,
        query="Where should I report my stolen bike?",
        jurisdiction="Assam",
        analysis=result.analysis,
    )

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_general_civic_query_routes_civic():
    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query="Tell me about Aadhaar services in Assam",
    )

    assert result.route == "civic"

    assert (
        result.analysis.intent
        == LegalIntent.GENERAL_CIVIC
    )

    assert result.retrieval_performed is False

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_verified_evidence_returns_safe_legal_answer():
    from app.models.legal_chunk import LegalChunk
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is the punishment for theft?"
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content="Test legal text.",
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query=(
                "What is the punishment for theft?"
            ),
            retrieval_performed=True,
        )
    )

    legal_answer_generator = AsyncMock()

    legal_answer_generator.generate.return_value = (
        LegalAnswer(
            summary=(
                "I do not have enough verified "
                "legal evidence to answer this question."
            ),
            caveats=[
                "The available legal evidence is insufficient."
            ],
        )
    )

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is the punishment for theft?",
        )

    assert result.route == "legal"
    assert result.retrieval_performed is True
    assert result.evidence == []

    assert result.legal_answer is not None

    assert (
        "not have enough verified"
        in result.legal_answer.summary
    )

    assert result.citation_validation is None
    assert result.claim_validation is None


@pytest.mark.asyncio
async def test_verified_legal_pipeline_runs_validation():
    from app.models.legal_chunk import LegalChunk
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is theft?"
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content=(
            "Whoever takes movable property dishonestly "
            "without consent commits theft."
        ),
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query="What is theft?",
            retrieval_performed=True,
        )
    )

    evidence = LegalEvidence(
        chunk_id=1,
        content=(
            "Whoever takes movable property dishonestly "
            "without consent commits theft."
        ),
        act_name="Bharatiya Nyaya Sanhita, 2023",
        act_short_name="BNS",
        version_label="BNS 2023 — Original",
        section_number="303",
        section_title="Theft",
        source_name="BNS Gazette",
        source_publisher="Ministry of Home Affairs",
        source_url="https://example.com",
        is_verified=True,
    )

    legal_answer_generator.generate.return_value = (
        LegalAnswer(
            summary=(
                "Taking movable property dishonestly "
                "without consent can constitute theft."
            ),
            legal_basis=[
                (
                    "Taking movable property dishonestly "
                    "without consent can constitute theft."
                )
            ],
            citations=["E1"],
        )
    )

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[evidence],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is theft?",
        )

    assert result.route == "legal"
    assert result.retrieval_performed is True

    assert len(result.evidence) == 1
    assert result.evidence[0].citation_id == "E1"

    assert result.legal_answer is not None

    assert result.citation_validation is not None
    assert result.citation_validation.is_valid is True

    assert result.claim_validation is not None
    assert result.claim_validation.is_valid is True

    assert result.answer_integrity is not None
    assert result.answer_integrity.is_valid is True

    assert result.answer_blocked is False
    assert result.safety_reason is None

    legal_answer_generator.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_generated_citation_blocks_legal_answer():
    from app.models.legal_chunk import LegalChunk
    from app.schemas.legal_evidence import LegalEvidence
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is theft?"
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content=(
            "Whoever takes movable property dishonestly "
            "without consent commits theft."
        ),
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query="What is theft?",
            retrieval_performed=True,
        )
    )

    evidence = LegalEvidence(
        chunk_id=1,
        content=(
            "Whoever takes movable property dishonestly "
            "without consent commits theft."
        ),
        act_name="Bharatiya Nyaya Sanhita, 2023",
        act_short_name="BNS",
        version_label="BNS 2023 — Original",
        section_number="303",
        section_title="Theft",
        source_name="BNS Gazette",
        source_publisher="Ministry of Home Affairs",
        source_url="https://example.com",
        is_verified=True,
    )

    legal_answer_generator.generate.return_value = LegalAnswer(
        summary="Test answer.",
        legal_basis=[
            (
                "Taking movable property dishonestly "
                "without consent can constitute theft."
            )
        ],
        citations=["E99"],
    )

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[evidence],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is theft?",
        )

    assert result.route == "legal"
    assert result.answer_blocked is True
    assert result.safety_reason is not None

    assert result.citation_validation is not None
    assert result.citation_validation.is_valid is False

    assert result.legal_answer is not None
    assert result.legal_answer.citations == []

    assert (
        "cannot safely provide"
        in result.legal_answer.summary.lower()
    )


@pytest.mark.asyncio
async def test_unsupported_legal_claim_blocks_answer():
    from app.models.legal_chunk import LegalChunk
    from app.schemas.legal_evidence import LegalEvidence
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is theft?"
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content=(
            "Whoever takes movable property dishonestly "
            "without consent commits theft."
        ),
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query="What is theft?",
            retrieval_performed=True,
        )
    )

    evidence = LegalEvidence(
        chunk_id=1,
        content=(
            "Whoever takes movable property dishonestly "
            "without consent commits theft."
        ),
        act_name="Bharatiya Nyaya Sanhita, 2023",
        act_short_name="BNS",
        version_label="BNS 2023 — Original",
        section_number="303",
        section_title="Theft",
        source_name="BNS Gazette",
        source_publisher="Ministry of Home Affairs",
        source_url="https://example.com",
        is_verified=True,
    )

    legal_answer_generator.generate.return_value = LegalAnswer(
        summary="Test answer.",
        legal_basis=[
            (
                "Every theft offence automatically results "
                "in ten years of imprisonment."
            )
        ],
        citations=["E1"],
    )

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[evidence],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is theft?",
        )

    assert result.answer_blocked is True

    assert result.citation_validation is not None
    assert result.citation_validation.is_valid is True

    assert result.claim_validation is not None
    assert result.claim_validation.is_valid is False

    assert result.legal_answer is not None
    assert result.legal_answer.legal_basis == []
    assert result.legal_answer.citations == []

    assert result.safety_reason is not None

@pytest.mark.asyncio
async def test_answer_integrity_failure_blocks_legal_answer():
    from app.models.legal_chunk import LegalChunk
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is the punishment for theft?"
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content=(
            "Whoever commits theft may be punished with "
            "imprisonment up to three years. "
            "Provided that where the value is below five "
            "thousand rupees, and the person is a first-time "
            "offender, and upon return of the property or "
            "restoration of the property, the person shall "
            "be punished with community service."
        ),
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query=(
                "What is the punishment for theft?"
            ),
            retrieval_performed=True,
        )
    )

    evidence = LegalEvidence(
        chunk_id=1,
        content=(
            "Whoever commits theft may be punished with "
            "imprisonment up to three years. "
            "Provided that where the value is below five "
            "thousand rupees, and the person is a first-time "
            "offender, and upon return of the property or "
            "restoration of the property, the person shall "
            "be punished with community service."
        ),
        act_name="Test Act",
        act_short_name="TEST",
        version_label="Test Version",
        section_number="10",
        section_title="Test offence",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )

    legal_answer_generator.generate.return_value = (
        LegalAnswer(
            summary=(
                "Where the value is below five thousand "
                "rupees and the person is a first-time "
                "offender, the person may receive "
                "community service."
            ),
            citations=["E1"],
        )
    )

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[evidence],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is the punishment for theft?",
        )

    # Citation and lexical claim grounding should pass.
    # The third integrity layer is what must block
    # the incomplete conditional rule.

    assert result.citation_validation is not None
    assert result.citation_validation.is_valid is True

    assert result.claim_validation is not None
    assert result.claim_validation.is_valid is True

    assert result.answer_integrity is not None
    assert result.answer_integrity.is_valid is False

    assert result.answer_blocked is True
    assert result.safety_reason is not None

    assert result.legal_answer is not None
    assert result.legal_answer.citations == []

@pytest.mark.asyncio
async def test_answer_integrity_failure_retries_once_and_returns_corrected_answer():
    from app.models.legal_chunk import LegalChunk
    from app.schemas.legal_evidence import LegalEvidence
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is the punishment for theft?"
    )

    legal_text = (
        "Whoever commits theft shall be punished with "
        "imprisonment which may extend to three years, "
        "or with fine, or with both. "
        "A person convicted for the second or subsequent "
        "time under this section shall be punished with "
        "rigorous imprisonment for a term not less than "
        "one year but which may extend to five years "
        "and with fine. "
        "Provided that in cases of theft where the value "
        "of the property is less than five thousand rupees, "
        "and a person is convicted for the first time, "
        "upon return of the value of property or restoration "
        "of the stolen property, the person shall be "
        "punished with community service."
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content=legal_text,
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query=(
                "What is the punishment for theft?"
            ),
            retrieval_performed=True,
        )
    )

    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=legal_text,
        act_name="Test Act",
        act_short_name="TA",
        version_label="Test Version",
        section_number="10",
        section_title="Theft",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )

    first_answer = LegalAnswer(
        summary=(
            "Theft may be punished with imprisonment "
            "up to three years, or fine, or both. "
            "For theft of property worth less than five "
            "thousand rupees, a first-time offender may "
            "receive community service."
        ),
        citations=["E1"],
    )

    corrected_answer = LegalAnswer(
        summary=(
            "Theft may be punished with imprisonment "
            "up to three years, or fine, or both. "
            "For a second or subsequent conviction under "
            "the section, punishment is rigorous "
            "imprisonment from one to five years and fine. "
            "Where the property value is below five thousand "
            "rupees, the person is convicted for the first "
            "time, and the property value is returned or "
            "the stolen property is restored, punishment "
            "is community service."
        ),
        citations=["E1"],
    )

    legal_answer_generator.generate.side_effect = [
        first_answer,
        corrected_answer,
    ]

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[evidence],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is the punishment for theft?",
        )

    # Retrieval must happen only once.
    legal_retrieval.retrieve.assert_awaited_once()

    # Exactly one regeneration attempt is allowed.
    assert legal_answer_generator.generate.await_count == 2

    first_call = (
        legal_answer_generator
        .generate.await_args_list[0]
    )

    second_call = (
        legal_answer_generator
        .generate.await_args_list[1]
    )

    assert (
        first_call.kwargs.get(
            "retry_mode",
            False,
        )
        is False
    )

    assert (
        second_call.kwargs["retry_mode"]
        is True
    )

    assert (
    "integrity_issue_codes"
    in second_call.kwargs
    )

    assert (
    "incomplete_qualified_rule"
    in second_call.kwargs[
        "integrity_issue_codes"
    ]
)

    assert result.answer_blocked is False
    assert result.safety_reason is None

    assert result.citation_validation is not None
    assert result.citation_validation.is_valid is True

    assert result.claim_validation is not None
    assert result.claim_validation.is_valid is True

    assert result.answer_integrity is not None
    assert result.answer_integrity.is_valid is True

    assert result.legal_answer is not None

    assert (
        result.legal_answer.summary
        == corrected_answer.summary
    )

    assert result.legal_answer.citations == ["E1"]


@pytest.mark.asyncio
async def test_answer_integrity_retry_propagates_omitted_qualified_rule():
    from app.models.legal_chunk import LegalChunk
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is the punishment for theft?"
    )

    legal_text = (
        "Whoever commits theft shall be punished with "
        "imprisonment which may extend to three years, "
        "or with fine, or with both. "
        "A person convicted for the second or subsequent "
        "time under this section shall be punished with "
        "rigorous imprisonment for a term not less than "
        "one year but which may extend to five years "
        "and with fine. "
        "Provided that in cases of theft where the value "
        "of the property is less than five thousand rupees, "
        "and a person is convicted for the first time, "
        "upon return of the value of property or restoration "
        "of the stolen property, the person shall be "
        "punished with community service."
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content=legal_text,
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query=(
                "What is the punishment for theft?"
            ),
            retrieval_performed=True,
        )
    )

    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=legal_text,
        act_name="Test Act",
        act_short_name="TA",
        version_label="Test Version",
        section_number="10",
        section_title="Theft",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )

    first_answer = LegalAnswer(
        summary=(
            "Theft may be punished with imprisonment "
            "up to three years, or fine, or both. "
            "For a second or subsequent conviction under "
            "the section, punishment is rigorous "
            "imprisonment from one to five years and fine."
        ),
        citations=["E1"],
    )

    corrected_answer = LegalAnswer(
        summary=(
            "Theft may be punished with imprisonment "
            "up to three years, or fine, or both. "
            "For a second or subsequent conviction under "
            "the section, punishment is rigorous "
            "imprisonment from one to five years and fine. "
            "Where the property value is below five thousand "
            "rupees, the person is convicted for the first "
            "time, and the property value is returned or "
            "the stolen property is restored, punishment "
            "is community service."
        ),
        citations=["E1"],
    )

    legal_answer_generator.generate.side_effect = [
        first_answer,
        corrected_answer,
    ]

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[evidence],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is the punishment for theft?",
        )

    legal_retrieval.retrieve.assert_awaited_once()
    assert legal_answer_generator.generate.await_count == 2

    second_call = (
        legal_answer_generator
        .generate.await_args_list[1]
    )

    assert second_call.kwargs["retry_mode"] is True
    assert "integrity_issue_codes" in second_call.kwargs
    assert (
        "omitted_qualified_rule"
        in second_call.kwargs["integrity_issue_codes"]
    )
    assert (
        second_call.kwargs[
            "omitted_qualified_rule_counts"
        ]
        == {
            "E1": 1,
        }
    )

    assert result.answer_blocked is False
    assert result.answer_integrity is not None
    assert result.answer_integrity.is_valid is True

@pytest.mark.asyncio
async def test_answer_integrity_retry_failure_blocks_without_third_attempt():
    from app.models.legal_chunk import LegalChunk
    from app.schemas.legal_evidence import LegalEvidence
    from app.services.legal_retrieval_orchestrator import (
        LegalRetrievalResult,
    )
    from app.services.query_analyzer import QueryAnalyzer

    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    analysis = QueryAnalyzer().analyze(
        "What is the punishment for theft?"
    )

    legal_text = (
        "Whoever commits theft shall be punished with "
        "imprisonment which may extend to three years, "
        "or with fine, or with both. "
        "A person convicted for the second or subsequent "
        "time under this section shall be punished with "
        "rigorous imprisonment for a term not less than "
        "one year but which may extend to five years "
        "and with fine. "
        "Provided that in cases of theft where the value "
        "of the property is less than five thousand rupees, "
        "and a person is convicted for the first time, "
        "upon return of the value of property or restoration "
        "of the stolen property, the person shall be "
        "punished with community service."
    )

    fake_chunk = LegalChunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content=legal_text,
    )

    legal_retrieval.retrieve.return_value = (
        LegalRetrievalResult(
            analysis=analysis,
            chunks=[fake_chunk],
            retrieval_query=(
                "What is the punishment for theft?"
            ),
            retrieval_performed=True,
        )
    )

    evidence = LegalEvidence(
        citation_id="E1",
        chunk_id=1,
        content=legal_text,
        act_name="Test Act",
        act_short_name="TA",
        version_label="Test Version",
        section_number="10",
        section_title="Theft",
        source_name="Test Gazette",
        source_publisher="Test Publisher",
        source_url="https://example.com",
        is_verified=True,
    )

    first_bad_answer = LegalAnswer(
        summary=(
            "For theft of property worth less than "
            "five thousand rupees, a first-time offender "
            "may receive community service."
        ),
        citations=["E1"],
    )

    second_bad_answer = LegalAnswer(
        summary=(
            "A first-time offender may receive "
            "community service when the property value "
            "is below five thousand rupees."
        ),
        citations=["E1"],
    )

    legal_answer_generator.generate.side_effect = [
        first_bad_answer,
        second_bad_answer,
    ]

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    with patch(
        "app.services.query_orchestrator.build_legal_evidence",
        new_callable=AsyncMock,
        return_value=[evidence],
    ):
        result = await orchestrator.handle(
            db=None,
            query="What is the punishment for theft?",
        )

    # Retrieval remains a single operation.
    legal_retrieval.retrieve.assert_awaited_once()

    # Initial generation + exactly one correction retry.
    assert legal_answer_generator.generate.await_count == 2

    second_call = (
        legal_answer_generator
        .generate.await_args_list[1]
    )

    assert (
        second_call.kwargs["retry_mode"]
        is True
    )

    # The second invalid answer must be blocked.
    assert result.answer_blocked is True
    assert result.safety_reason is not None

    assert result.answer_integrity is not None
    assert result.answer_integrity.is_valid is False

    assert result.legal_answer is not None

    # Public-safe fallback must replace the invalid draft.
    assert result.legal_answer.citations == []


@pytest.mark.asyncio
async def test_public_service_query_routes_civic_without_rag():
    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query="How can I report a problem with a public service?",
        jurisdiction="Assam",
    )

    assert result.route == "civic"
    assert result.analysis.intent == LegalIntent.GENERAL_CIVIC
    assert result.analysis.domain.value == "government_services"
    assert result.analysis.jurisdiction == "Assam"
    assert result.analysis.requires_follow_up is False
    assert result.retrieval_performed is False

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_water_supply_query_routes_civic_without_rag():
    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query=(
            "How can I complain about an ongoing "
            "public water-supply problem?"
        ),
        jurisdiction="Assam",
    )

    assert result.route == "civic"
    assert result.analysis.intent == LegalIntent.GENERAL_CIVIC
    assert result.analysis.domain.value == "government_services"
    assert result.analysis.jurisdiction == "Assam"
    assert result.analysis.requires_follow_up is False
    assert result.retrieval_performed is False

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_cat_joke_query_routes_out_of_scope_without_rag():
    legal_retrieval = AsyncMock()
    legal_answer_generator = AsyncMock()

    orchestrator = QueryOrchestrator(
        legal_retrieval_orchestrator=legal_retrieval,
        legal_answer_generator=legal_answer_generator,
    )

    result = await orchestrator.handle(
        db=None,
        query="Tell me a joke about cats.",
    )

    assert result.route == "out_of_scope"
    assert result.analysis.intent == LegalIntent.OUT_OF_SCOPE
    assert result.retrieval_performed is False

    legal_retrieval.retrieve.assert_not_awaited()
    legal_answer_generator.generate.assert_not_awaited()
