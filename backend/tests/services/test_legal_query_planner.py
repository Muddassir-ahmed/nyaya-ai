from unittest.mock import AsyncMock

import pytest

from app.schemas.legal_query_plan import (
    LegalCorpusHint,
    LegalQuestionAspect,
)
from app.schemas.llm import LLMResponse
from app.services.legal_query_planner import (
    LegalQueryPlanner,
    deterministic_legal_bridges,
)
from app.services.query_analyzer import QueryAnalyzer


def test_molded_bns_question_requires_query_expansion():
    analysis = QueryAnalyzer().analyze(
        "What is the provision for mob lynching under the BNS, "
        "and what is the punishment?"
    )

    assert LegalQueryPlanner.should_expand(
        analysis
    ) is True


def test_existing_qualifier_aware_canonical_query_is_not_replanned():
    analysis = QueryAnalyzer().analyze(
        "A person intentionally hit me without any provocation. "
        "Which BNS provisions may apply?"
    )

    assert analysis.rewritten_queries[0] == (
        "assault or criminal force otherwise than on "
        "grave and sudden provocation"
    )

    assert LegalQueryPlanner.should_expand(
        analysis
    ) is False


def test_ordinary_theft_facts_do_not_trigger_snatching_bridge():
    query = (
        "A person dishonestly moved another person's movable property "
        "without consent in order to take it. Which BNS offence "
        "describes this?"
    )

    assert deterministic_legal_bridges(query) == []

    possession_query = (
        "A person took movable property out of someone else's "
        "possession without consent. Which BNS offence describes it?"
    )

    assert deterministic_legal_bridges(possession_query) == []


@pytest.mark.asyncio
async def test_planner_returns_sanitized_retrieval_hypotheses():
    provider = AsyncMock()
    provider.generate.return_value = LLMResponse(
        content=(
            '{'
            '"search_queries": ['
            '" group acting in concert commits murder ", '
            '"punishment for group murder", '
            '"GROUP ACTING IN CONCERT COMMITS MURDER"'
            '], '
            '"corpus_hint": "bns", '
            '"requested_aspects": ["applicability", "punishment"], '
            '"ambiguity_notes": ["Whether the statutory conditions are met"]'
            '}'
        ),
        model="test-model",
        provider="test",
    )

    planner = LegalQueryPlanner(
        provider=provider
    )

    query = (
        "What is the provision for mob lynching under the BNS, "
        "and what is the punishment?"
    )
    analysis = QueryAnalyzer().analyze(query)

    plan = await planner.plan(
        user_query=query,
        analysis=analysis,
    )

    assert plan.search_queries == [
        (
            "group of five or more persons acting in concert "
            "commits murder on specified grounds"
        ),
        "group acting in concert commits murder",
        "punishment for group murder",
    ]
    assert plan.corpus_hint == LegalCorpusHint.BNS
    assert plan.requested_aspects == [
        LegalQuestionAspect.APPLICABILITY,
        LegalQuestionAspect.PUNISHMENT,
    ]

    request = provider.generate.await_args.args[0]

    assert request.temperature == 0.0
    assert request.response_schema is not None


@pytest.mark.asyncio
async def test_planner_rejects_invented_section_reference():
    provider = AsyncMock()
    provider.generate.return_value = LLMResponse(
        content=(
            '{'
            '"search_queries": ['
            '"Section 103 mob lynching", '
            '"group acting in concert commits murder"'
            '], '
            '"corpus_hint": "bns", '
            '"requested_aspects": ["punishment"], '
            '"ambiguity_notes": []'
            '}'
        ),
        model="test-model",
        provider="test",
    )

    planner = LegalQueryPlanner(
        provider=provider
    )

    query = "What is the punishment for mob lynching under BNS?"

    plan = await planner.plan(
        user_query=query,
        analysis=QueryAnalyzer().analyze(query),
    )

    assert plan.search_queries == [
        (
            "group of five or more persons acting in concert "
            "commits murder on specified grounds"
        ),
        "group acting in concert commits murder"
    ]
    assert all(
        "Section 103" not in query
        for query in plan.search_queries
    )


@pytest.mark.asyncio
async def test_planner_failure_keeps_deterministic_mob_lynching_bridge():
    provider = AsyncMock()
    provider.generate.side_effect = RuntimeError(
        "planner unavailable"
    )

    planner = LegalQueryPlanner(
        provider=provider
    )

    query = "Explain mob lynching under BNS"

    plan = await planner.plan(
        user_query=query,
        analysis=QueryAnalyzer().analyze(query),
    )

    assert plan.search_queries == [
        (
            "group of five or more persons acting in concert "
            "commits murder on specified grounds"
        )
    ]


@pytest.mark.asyncio
async def test_snatching_factual_bridge_precedes_unstable_model_hypotheses():
    provider = AsyncMock()
    provider.generate.return_value = LLMResponse(
        content=(
            '{'
            '"search_queries": ['
            '"Bharatiya Nyaya Sanhita theft by servant", '
            '"BNS offence for theft by sudden taking", '
            '"BNS offence for taking property without consent"'
            '], '
            '"corpus_hint": "bns", '
            '"requested_aspects": ["definition"], '
            '"ambiguity_notes": []'
            '}'
        ),
        model="test-model",
        provider="test",
    )

    planner = LegalQueryPlanner(provider=provider)
    query = (
        "A motorcyclist quickly yanked a bag from a person's hand "
        "and rode away. Which BNS offence describes this?"
    )

    plan = await planner.plan(
        user_query=query,
        analysis=QueryAnalyzer().analyze(query),
    )

    assert plan.search_queries[0] == (
        "theft is snatching if the offender suddenly quickly or "
        "forcibly seizes secures grabs or takes away movable property "
        "from a person or possession"
    )
    assert len(plan.search_queries) == 3


@pytest.mark.asyncio
async def test_mob_lynching_bridge_precedes_generic_model_wording():
    provider = AsyncMock()
    provider.generate.return_value = LLMResponse(
        content=(
            '{'
            '"search_queries": ['
            '"Bharatiya Nyaya Sanhita mob lynching provision", '
            '"BNS punishment for mob lynching"'
            '], '
            '"corpus_hint": "bns", '
            '"requested_aspects": ["punishment"], '
            '"ambiguity_notes": []'
            '}'
        ),
        model="test-model",
        provider="test",
    )

    planner = LegalQueryPlanner(provider=provider)
    query = (
        "What provision covers lynching by a mob under the BNS, "
        "and what punishment can apply?"
    )

    plan = await planner.plan(
        user_query=query,
        analysis=QueryAnalyzer().analyze(query),
    )

    assert plan.search_queries[0] == (
        "group of five or more persons acting in concert commits "
        "murder on specified grounds"
    )


@pytest.mark.asyncio
async def test_planner_transport_failure_falls_back_to_empty_expansion():
    provider = AsyncMock()
    provider.generate.side_effect = Exception(
        "transport unavailable"
    )

    planner = LegalQueryPlanner(
        provider=provider
    )

    query = "Explain a group attack under BNS"

    plan = await planner.plan(
        user_query=query,
        analysis=QueryAnalyzer().analyze(query),
    )

    assert plan.search_queries == []
