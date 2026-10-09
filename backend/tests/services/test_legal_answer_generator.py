import json

import pytest

from app.schemas.legal_evidence import LegalEvidence
from app.schemas.llm import LLMResponse
from app.services.legal_answer_generator import (
    LegalAnswerGenerator,
)
from app.services.llm_provider import LLMProvider


class FakeLLMProvider(LLMProvider):

    def __init__(self, response: str):
        self.response = response
        self.last_request = None

    async def generate(self, request):
        self.last_request = request

        return LLMResponse(
            content=self.response,
            model="fake-model",
            provider="fake",
        )


def make_evidence() -> LegalEvidence:

    return LegalEvidence(
        chunk_id=1,
        content="Test legal provision.",

        act_name=(
            "Bharatiya Nyaya Sanhita, 2023"
        ),

        act_short_name="BNS",

        version_label=(
            "BNS 2023 — Original"
        ),

        section_number="303",

        section_title="Theft",

        source_name=(
            "Bharatiya Nyaya Sanhita, 2023 — Gazette"
        ),

        source_publisher=(
            "Ministry of Home Affairs, "
            "Government of India"
        ),

        source_url="https://www.mha.gov.in/",

        is_verified=True,
    )


@pytest.mark.asyncio
async def test_generator_returns_structured_answer():

    response = {
        "summary": "This is a test answer.",
        "legal_basis": [
            "The supplied evidence contains the relevant provision."
        ],
        "possible_options": [
            "Review the applicable legal provision."
        ],
        "evidence_to_preserve": [
            "Keep relevant records."
        ],
        "next_steps": [
            "Seek appropriate assistance if necessary."
        ],
        "caveats": [
            "This is general legal information."
        ],
        "citations": [
            "Bharatiya Nyaya Sanhita, 2023, Section 303"
        ],
    }

    provider = FakeLLMProvider(
        json.dumps(response)
    )

    generator = LegalAnswerGenerator(
        provider
    )

    answer = await generator.generate(
        user_query="What is theft?",
        evidence=[make_evidence()],
    )

    assert (
        answer.summary
        == "This is a test answer."
    )

    assert len(answer.legal_basis) == 1
    assert len(answer.citations) == 1


@pytest.mark.asyncio
async def test_generator_handles_empty_evidence():

    provider = FakeLLMProvider(
        "{}"
    )

    generator = LegalAnswerGenerator(
        provider
    )

    answer = await generator.generate(
        user_query="What is theft?",
        evidence=[],
    )

    assert (
        "not have enough verified"
        in answer.summary
    )


@pytest.mark.asyncio
async def test_generator_handles_non_json_response():

    provider = FakeLLMProvider(
        "This is an unstructured answer."
    )

    generator = LegalAnswerGenerator(
        provider
    )

    answer = await generator.generate(
        user_query="What is theft?",
        evidence=[make_evidence()],
    )

    assert (
        answer.summary
        == "This is an unstructured answer."
    )

    assert len(answer.caveats) == 1

@pytest.mark.asyncio
async def test_generator_requests_structured_output():
    evidence = make_evidence()

    evidence.citation_id = "E1"

    response = {
        "summary": "Test answer.",
        "legal_basis": [],
        "possible_options": [],
        "evidence_to_preserve": [],
        "next_steps": [],
        "caveats": [],
        "citations": ["E1"],
    }

    provider = FakeLLMProvider(
        json.dumps(response)
    )

    generator = LegalAnswerGenerator(
        provider
    )

    answer = await generator.generate(
        user_query="What is theft?",
        evidence=[evidence],
    )

    assert answer.citations == ["E1"]

    assert provider.last_request is not None

    assert (
        provider.last_request.temperature
        == 0.0
    )

    assert (
        provider.last_request.response_schema
        is not None
    )

    schema = (
        provider.last_request.response_schema
    )

    assert (
        schema["additionalProperties"]
        is False
    )

    assert set(
        schema["required"]
    ) == {
        "summary",
        "legal_basis",
        "possible_options",
        "evidence_to_preserve",
        "next_steps",
        "caveats",
        "citations",
    }

    citation_schema = (
        schema["properties"]["citations"]
    )

    assert (
        citation_schema["items"]["enum"]
        == ["E1"]
    )

    assert (
        citation_schema["minItems"]
        == 1
    )

def test_response_schema_restricts_citation_ids():
    evidence_1 = make_evidence()
    evidence_1.citation_id = "E1"

    evidence_2 = make_evidence()
    evidence_2.citation_id = "E2"

    schema = (
        LegalAnswerGenerator
        ._build_response_schema(
            [
                evidence_1,
                evidence_2,
            ]
        )
    )

    citation_schema = (
        schema["properties"]["citations"]
    )

    assert (
        citation_schema["items"]["enum"]
        == [
            "E1",
            "E2",
        ]
    )

@pytest.mark.asyncio
async def test_retry_mode_adds_correction_instructions_without_changing_evidence_schema():
    evidence = make_evidence()
    evidence.citation_id = "E1"

    response = {
        "summary": "Test answer.",
        "legal_basis": [],
        "possible_options": [],
        "evidence_to_preserve": [],
        "next_steps": [],
        "caveats": [],
        "citations": ["E1"],
    }

    normal_provider = FakeLLMProvider(
        json.dumps(response)
    )

    retry_provider = FakeLLMProvider(
        json.dumps(response)
    )

    normal_generator = LegalAnswerGenerator(
        normal_provider
    )

    retry_generator = LegalAnswerGenerator(
        retry_provider
    )

    await normal_generator.generate(
        user_query="What is the punishment for theft?",
        evidence=[evidence],
    )

    await retry_generator.generate(
        user_query="What is the punishment for theft?",
        evidence=[evidence],
        retry_mode=True,
    )

    assert normal_provider.last_request is not None
    assert retry_provider.last_request is not None

    normal_prompt = (
        normal_provider
        .last_request
        .messages[1]
        .content
    )

    retry_prompt = (
        retry_provider
        .last_request
        .messages[1]
        .content
    )

    assert "CORRECTION RETRY:" not in normal_prompt

    assert "CORRECTION RETRY:" in retry_prompt

    assert (
        "The previous generated draft failed "
        "NyayaAI's"
        in retry_prompt
    )

    assert (
        "Do not rely on or reproduce the previous draft."
        in retry_prompt
    )

    # The retry must still use the same verified evidence.
    assert "Test legal provision." in normal_prompt
    assert "Test legal provision." in retry_prompt

    assert "[E1]" in normal_prompt
    assert "[E1]" in retry_prompt

    # Retry mode must not weaken the structured-output
    # contract or citation restrictions.
    assert (
        normal_provider.last_request.response_schema
        == retry_provider.last_request.response_schema
    )

    citation_schema = (
        retry_provider
        .last_request
        .response_schema[
            "properties"
        ][
            "citations"
        ]
    )

    assert (
        citation_schema["items"]["enum"]
        == ["E1"]
    )

    # Generation remains deterministic.
    assert (
        retry_provider.last_request.temperature
        == 0.0
    )

@pytest.mark.asyncio
async def test_retry_mode_includes_targeted_integrity_feedback():
    evidence = make_evidence()
    evidence.citation_id = "E1"

    response = {
        "summary": "Test answer.",
        "legal_basis": [],
        "possible_options": [],
        "evidence_to_preserve": [],
        "next_steps": [],
        "caveats": [],
        "citations": ["E1"],
    }

    provider = FakeLLMProvider(
        json.dumps(response)
    )

    generator = LegalAnswerGenerator(
        provider
    )

    await generator.generate(
    user_query="What is the punishment?",
    evidence=[evidence],
    retry_mode=True,
    integrity_issue_codes=[
        "omitted_qualified_rule",
    ],
    omitted_qualified_rule_counts={
    "E1": 1,
    },
)

    assert provider.last_request is not None

    prompt = (
        provider
        .last_request
        .messages[1]
        .content
    )

    assert (
        "omitted_qualified_rule"
        in prompt
    )

    assert (
        "At least one material qualified legal consequence"
        in prompt
    )

    assert (
        "every distinct qualified legal consequence"
        in prompt
    )

    assert (
        "Treat each separate qualified consequence as a checklist item."
        in prompt
    )

    assert (
        "The final answer must account for every material checklist item"
        in prompt
    )

    assert (
        "If the controlling evidence contains multiple distinct qualified consequences"
        in prompt
    )

    assert (
        "include each one with all of its attached conditions"
        in prompt
    )

    assert (
        "STRUCTURED COMPLETENESS TARGETS:"
        in prompt
    )

    assert (
        "E1 has 1 omitted qualified"
        in prompt
    )

    assert (
        "These counts refer to rules detected as missing"
        in prompt
    )

    assert (
        "Do not invent rules to satisfy the count."
        in prompt
    )


@pytest.mark.asyncio
async def test_prompt_requires_direct_reference_citation_alignment():
    evidence = make_evidence()
    evidence.citation_id = "E1"

    response = {
        "summary": "Test answer.",
        "legal_basis": [],
        "possible_options": [],
        "evidence_to_preserve": [],
        "next_steps": [],
        "caveats": [],
        "citations": ["E1"],
    }

    provider = FakeLLMProvider(json.dumps(response))
    generator = LegalAnswerGenerator(provider)

    await generator.generate(
        user_query="What does the provision say?",
        evidence=[evidence],
    )

    prompt = provider.last_request.messages[1].content

    assert (
        "Every cited evidence ID must directly support"
        in prompt
    )
    assert (
        "structured metadata matches that exact legal"
        in prompt
    )
