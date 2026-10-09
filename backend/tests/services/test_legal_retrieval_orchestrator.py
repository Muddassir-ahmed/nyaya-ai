from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.legal_chunk import LegalChunk
from app.schemas.legal_query_plan import LegalQueryPlan
from app.services.legal_corpus_context import (
    LegalCorpusContext,
)
from app.services.legal_retrieval_orchestrator import (
    LegalRetrievalOrchestrator,
)


def make_isolated_orchestrator() -> LegalRetrievalOrchestrator:
    """Build retrieval tests without contacting the configured LLM."""
    planner = MagicMock()
    planner.should_expand.return_value = False
    planner.plan = AsyncMock(
        return_value=LegalQueryPlan()
    )

    return LegalRetrievalOrchestrator(
        query_planner=planner
    )


@pytest.mark.asyncio
async def test_emergency_does_not_call_rag():
    orchestrator = make_isolated_orchestrator()

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
    ) as mock_rag:

        result = await orchestrator.retrieve(
            db=None,
            query=(
                "Someone is threatening to kill me right now "
                "and is standing outside my home."
            ),
        )

    assert result.analysis.intent.value == "emergency"
    assert result.retrieval_performed is False
    assert result.chunks == []

    mock_rag.assert_not_awaited()


@pytest.mark.asyncio
async def test_authority_lookup_does_not_call_rag():
    orchestrator = make_isolated_orchestrator()

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
    ) as mock_rag:

        result = await orchestrator.retrieve(
            db=None,
            query="Where should I report my stolen bike?",
        )

    assert result.analysis.intent.value == "authority_lookup"
    assert result.retrieval_performed is False
    assert result.chunks == []

    mock_rag.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_jurisdiction_stops_retrieval():
    orchestrator = make_isolated_orchestrator()

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
    ) as mock_rag:

        result = await orchestrator.retrieve(
            db=None,
            query="How do I file a complaint about a local property dispute?",
        )

    assert result.analysis.requires_follow_up is True
    assert result.retrieval_performed is False
    assert result.chunks == []

    mock_rag.assert_not_awaited()


@pytest.mark.asyncio
async def test_normal_legal_query_calls_hybrid_retrieval():
    orchestrator = make_isolated_orchestrator()

    fake_chunk = LegalChunk(
        id=123,
        document_id=1,
        chunk_index=0,
        content="The punishment for theft is provided under the applicable law.",
    )

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
        return_value=[fake_chunk],
    ) as mock_rag:

        result = await orchestrator.retrieve(
            db=None,
            query="What is the punishment for theft?",
        )

    assert result.analysis.intent.value == "legal_information"
    assert result.retrieval_performed is True
    assert len(result.chunks) == 1
    assert result.chunks[0].id == 123

    mock_rag.assert_awaited_once()


@pytest.mark.asyncio
async def test_normal_legal_query_uses_rewritten_query():
    orchestrator = make_isolated_orchestrator()

    fake_chunk = LegalChunk(
        id=456,
        document_id=1,
        chunk_index=0,
        content="Theft-related legal provision.",
    )

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
        return_value=[fake_chunk],
    ) as mock_rag:

        result = await orchestrator.retrieve(
            db=None,
            query="What happens if someone steals my property?",
        )

    assert result.retrieval_performed is True

    called_kwargs = mock_rag.await_args.kwargs

    assert called_kwargs["query"] == result.retrieval_query
    assert called_kwargs["additional_queries"] == (
        result.retrieval_queries[1:]
    )
    assert called_kwargs["rerank_query"] == (
        "What happens if someone steals my property?"
    )
    assert called_kwargs["top_k"] == 5
    assert called_kwargs["candidate_k"] == 20


@pytest.mark.asyncio
async def test_user_jurisdiction_is_not_used_as_legal_filter():
    orchestrator = make_isolated_orchestrator()

    fake_chunk = LegalChunk(
        id=789,
        document_id=1,
        chunk_index=0,
        content="BNS legal provision related to theft.",
    )

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
        return_value=[fake_chunk],
    ) as mock_rag:

        result = await orchestrator.retrieve(
            db=None,
            query="What is the punishment for theft in Assam?",
        )

    assert result.user_jurisdiction == "AS"
    assert result.retrieval_performed is True
    assert len(result.chunks) == 1

    called_kwargs = mock_rag.await_args.kwargs

    assert called_kwargs["jurisdiction_id"] is None

@pytest.mark.asyncio
async def test_precomputed_analysis_can_satisfy_jurisdiction_requirement():
    from app.models.legal_chunk import LegalChunk
    from app.services.query_analyzer import QueryAnalyzer

    orchestrator = make_isolated_orchestrator()

    query = (
        "How do I file a complaint about "
        "a local property dispute?"
    )

    analysis = QueryAnalyzer().analyze(query)

    assert analysis.requires_follow_up is True

    resolved_analysis = analysis.model_copy(
        update={
            "jurisdiction": "Assam",
            "requires_follow_up": False,
            "missing_information": [],
        }
    )

    fake_chunk = LegalChunk(
        id=900,
        document_id=1,
        chunk_index=0,
        content="Test legal provision.",
    )

    with patch(
        "app.services.legal_retrieval_orchestrator."
        "hybrid_search_legal_chunks",
        new_callable=AsyncMock,
        return_value=[fake_chunk],
    ) as mock_rag:
        result = await orchestrator.retrieve(
            db=None,
            query=query,
            analysis=resolved_analysis,
        )

    assert result.retrieval_performed is True
    assert result.user_jurisdiction == "Assam"

    mock_rag.assert_awaited_once()


@pytest.mark.asyncio
async def test_theft_definition_uses_canonical_query_in_production_path():
    orchestrator = make_isolated_orchestrator()

    fake_chunk = LegalChunk(
        id=303,
        document_id=1,
        chunk_index=0,
        content="Section 303 definition of theft.",
    )

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
        return_value=[fake_chunk],
    ) as mock_rag:

        result = await orchestrator.retrieve(
            db=None,
            query="What is theft under the Bharatiya Nyaya Sanhita?",
        )

    called_kwargs = mock_rag.await_args.kwargs

    assert result.retrieval_performed is True
    assert result.retrieval_query == "theft"
    assert called_kwargs["query"] == "theft"
    assert called_kwargs["candidate_k"] == 20


@pytest.mark.asyncio
async def test_qualified_theft_definition_keeps_context_in_production_path():
    orchestrator = make_isolated_orchestrator()
    query = "What is theft committed in a human dwelling?"

    fake_chunk = LegalChunk(
        id=305,
        document_id=1,
        chunk_index=0,
        content="Section 305 theft in a human dwelling.",
    )

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
        return_value=[fake_chunk],
    ) as mock_rag:
        result = await orchestrator.retrieve(
            db=None,
            query=query,
        )

    expected = query.lower()
    called_kwargs = mock_rag.await_args.kwargs

    assert result.retrieval_performed is True
    assert result.retrieval_query == expected
    assert called_kwargs["query"] == expected
    assert called_kwargs["candidate_k"] == 20


@pytest.mark.asyncio
async def test_unprovoked_hitting_uses_qualifier_aware_retrieval_query():
    orchestrator = make_isolated_orchestrator()
    query = (
        "A person intentionally hit me without any provocation. "
        "Which BNS provisions may apply?"
    )

    fake_chunk = LegalChunk(
        id=131,
        document_id=1,
        chunk_index=0,
        content="Section 131 assault or criminal force.",
    )

    with patch(
        "app.services.legal_retrieval_orchestrator.hybrid_search_legal_chunks",
        new_callable=AsyncMock,
        return_value=[fake_chunk],
    ) as mock_rag:
        result = await orchestrator.retrieve(
            db=None,
            query=query,
        )

    expected = (
        "assault or criminal force otherwise than on "
        "grave and sudden provocation"
    )
    called_kwargs = mock_rag.await_args.kwargs

    assert result.retrieval_performed is True
    assert result.retrieval_query == expected
    assert called_kwargs["query"] == expected


@pytest.mark.asyncio
async def test_molded_bns_query_uses_planner_and_explicit_act_scope():
    planner = MagicMock()
    planner.should_expand.return_value = True
    planner.plan = AsyncMock(
        return_value=LegalQueryPlan(
            search_queries=[
                (
                    "group of five or more persons acting in concert "
                    "commits murder on specified grounds"
                ),
                "punishment for group murder",
            ]
        )
    )

    orchestrator = LegalRetrievalOrchestrator(
        query_planner=planner
    )

    query = (
        "What is the provision for mob lynching under the BNS, "
        "and what is the punishment?"
    )

    target = LegalChunk(
        id=103,
        document_id=2,
        act_id=1,
        version_id=1,
        chunk_index=0,
        content="Group acting in concert commits murder.",
    )

    with (
        patch(
            "app.services.legal_retrieval_orchestrator."
            "get_bns_context",
            new_callable=AsyncMock,
            return_value=LegalCorpusContext(
                act_id=1,
                version_id=7,
                legal_jurisdiction="IN",
            ),
        ) as bns_context,
        patch(
            "app.services.legal_retrieval_orchestrator."
            "hybrid_search_legal_chunks",
            new_callable=AsyncMock,
            return_value=[target],
        ) as mock_rag,
    ):
        result = await orchestrator.retrieve(
            db=object(),
            query=query,
        )

    planner.plan.assert_awaited_once()
    bns_context.assert_awaited_once()

    assert result.retrieval_performed is True
    assert result.legal_jurisdiction == "IN"
    assert result.chunks == [target]

    assert result.retrieval_queries == [
        query.lower(),
        (
            "group of five or more persons acting in concert "
            "commits murder on specified grounds"
        ),
        (
            "Indian criminal law provision mob lynching "
            "bns punishment"
        ),
        "punishment for group murder",
    ]

    called_kwargs = mock_rag.await_args.kwargs

    assert called_kwargs["query"] == query.lower()
    assert called_kwargs["additional_queries"] == [
        (
            "group of five or more persons acting in concert "
            "commits murder on specified grounds"
        ),
        (
            "Indian criminal law provision mob lynching "
            "bns punishment"
        ),
        "punishment for group murder",
    ]
    assert called_kwargs["additional_query_weights"] == [
        1.0,
        0.75,
        0.25,
    ]
    assert called_kwargs["rerank_query"] == query
    assert called_kwargs["top_k"] == 6
    assert called_kwargs["act_id"] == 1
    assert called_kwargs["version_id"] == 7


@pytest.mark.asyncio
async def test_article_21_focus_excludes_noisy_model_expansions():
    planner = MagicMock()
    planner.should_expand.return_value = True
    planner.plan = AsyncMock(
        return_value=LegalQueryPlan(
            search_queries=[
                "protection against deprivation of life and liberty",
                "constitutional protection against arbitrary detention",
                "procedure established by law for deprivation of liberty",
            ]
        )
    )
    orchestrator = LegalRetrievalOrchestrator(query_planner=planner)
    query = (
        "Which constitutional protection says that a person cannot be "
        "deprived of life or personal liberty except according to "
        "procedure established by law?"
    )
    article_21 = LegalChunk(
        id=21,
        document_id=1,
        act_id=1,
        version_id=1,
        section_id=21,
        chunk_index=0,
        content="Life and personal liberty.",
    )
    article_22 = LegalChunk(
        id=22,
        document_id=1,
        act_id=1,
        version_id=1,
        section_id=22,
        chunk_index=0,
        content="Protection against arrest and detention.",
    )

    with (
        patch(
            "app.services.legal_retrieval_orchestrator."
            "get_constitution_context",
            new_callable=AsyncMock,
            return_value=LegalCorpusContext(
                act_id=1,
                version_id=1,
                legal_jurisdiction="IN",
            ),
        ),
        patch(
            "app.services.legal_retrieval_orchestrator."
            "hybrid_search_legal_chunks",
            new_callable=AsyncMock,
            return_value=[article_21, article_22],
        ) as mock_rag,
        patch(
            "app.services.legal_retrieval_orchestrator.focus_legal_chunks",
            new_callable=AsyncMock,
            return_value=[article_21],
        ) as mock_focus,
    ):
        result = await orchestrator.retrieve(db=object(), query=query)

    assert result.chunks == [article_21]
    assert mock_rag.await_args.kwargs["additional_query_weights"] == [
        0.25,
        0.25,
        0.25,
    ]
    focus_queries = mock_focus.await_args.kwargs["retrieval_queries"]
    assert focus_queries == [query.lower()]
    assert "arbitrary detention" not in " ".join(focus_queries)


@pytest.mark.asyncio
async def test_threat_focus_keeps_analyzer_signal_but_not_model_guesses():
    planner = MagicMock()
    planner.should_expand.return_value = True
    planner.plan = AsyncMock(
        return_value=LegalQueryPlan(
            search_queries=[
                "Bharatiya Nyaya Sanhita threat",
                "BNS offence against intimidation",
                "BNS provision for coercion",
            ]
        )
    )
    orchestrator = LegalRetrievalOrchestrator(query_planner=planner)
    query = (
        "I am safe now, but someone threatened injury to frighten me "
        "into doing something. Which BNS offence may be relevant?"
    )
    target = LegalChunk(
        id=351,
        document_id=2,
        act_id=1,
        version_id=1,
        section_id=351,
        chunk_index=0,
        content="Threat of injury intended to cause alarm.",
    )

    with (
        patch(
            "app.services.legal_retrieval_orchestrator."
            "get_bns_context",
            new_callable=AsyncMock,
            return_value=LegalCorpusContext(
                act_id=1,
                version_id=1,
                legal_jurisdiction="IN",
            ),
        ),
        patch(
            "app.services.legal_retrieval_orchestrator."
            "hybrid_search_legal_chunks",
            new_callable=AsyncMock,
            return_value=[target],
        ) as mock_rag,
        patch(
            "app.services.legal_retrieval_orchestrator.focus_legal_chunks",
            new_callable=AsyncMock,
            return_value=[target],
        ) as mock_focus,
    ):
        result = await orchestrator.retrieve(db=object(), query=query)

    assert result.chunks == [target]
    assert mock_rag.await_args.kwargs["additional_query_weights"] == [
        0.75,
        0.25,
        0.25,
        0.25,
    ]
    focus_queries = mock_focus.await_args.kwargs["retrieval_queries"]
    assert focus_queries == [
        query.lower(),
        "Indian criminal law safe now but someone threatened injury "
        "frighten into",
    ]
    assert "coercion" not in " ".join(focus_queries)
