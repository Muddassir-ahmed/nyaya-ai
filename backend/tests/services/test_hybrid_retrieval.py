from unittest.mock import AsyncMock, patch

import pytest

from app.models.legal_chunk import LegalChunk
from app.services.hybrid_retrieval import (
    hybrid_search_legal_chunks,
)


def make_chunk(
    chunk_id: int,
    content: str,
) -> LegalChunk:
    return LegalChunk(
        id=chunk_id,
        document_id=2,
        act_id=1,
        version_id=1,
        chunk_index=0,
        content=content,
    )


@pytest.mark.asyncio
async def test_semantic_reranker_does_not_discard_strong_hybrid_candidate():
    """
    Regression guard:

    A candidate strongly supported by both vector and
    lexical retrieval must not disappear merely because
    the semantic reranker places it last.
    """

    primary = make_chunk(
        1,
        (
            "Whoever commits theft shall be punished "
            "with imprisonment which may extend to "
            "three years."
        ),
    )

    chunks = [
        primary,
        make_chunk(2, "Special theft provision two."),
        make_chunk(3, "Special theft provision three."),
        make_chunk(4, "Special theft provision four."),
        make_chunk(5, "Special theft provision five."),
        make_chunk(6, "Special theft provision six."),
    ]

    # Vector and lexical retrieval both strongly agree
    # that `primary` is the best candidate.
    vector_results = list(chunks)
    lexical_results = list(chunks)

    # Simulate a bad semantic reranker result that places
    # the primary provision last.
    semantic_results = list(
        reversed(chunks)
    )

    reranker = AsyncMock()
    reranker.rerank.return_value = (
        semantic_results
    )

    with (
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks",
            new_callable=AsyncMock,
            return_value=vector_results,
        ),
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks_lexical",
            new_callable=AsyncMock,
            return_value=lexical_results,
        ),
        patch(
            "app.services.hybrid_retrieval."
            "get_reranker_provider",
            return_value=reranker,
        ),
    ):
        results = await hybrid_search_legal_chunks(
            db=None,
            query="What is the punishment for theft?",
            top_k=5,
            candidate_k=6,
        )

    result_ids = [
        chunk.id
        for chunk in results
    ]

    assert primary.id in result_ids

    reranker.rerank.assert_awaited_once()

    call_kwargs = (
        reranker.rerank.await_args.kwargs
    )

    # Semantic ranking must see the whole candidate set,
    # not only the final top_k.
    assert call_kwargs["top_k"] == 6


@pytest.mark.asyncio
async def test_additional_query_can_recover_molded_legal_concept():
    unrelated = make_chunk(
        10,
        "General provision returned for the ordinary-language query.",
    )
    target = make_chunk(
        103,
        (
            "A group of five or more persons acting in concert "
            "commits murder on specified grounds."
        ),
    )

    async def vector_side_effect(*, query, **kwargs):
        if "acting in concert" in query:
            return [target]

        return [unrelated]

    async def lexical_side_effect(*, query, **kwargs):
        if "acting in concert" in query:
            return [target]

        return []

    reranker = AsyncMock()
    reranker.rerank.return_value = [
        target,
        unrelated,
    ]

    with (
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks",
            new_callable=AsyncMock,
            side_effect=vector_side_effect,
        ) as vector_search,
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks_lexical",
            new_callable=AsyncMock,
            side_effect=lexical_side_effect,
        ) as lexical_search,
        patch(
            "app.services.hybrid_retrieval."
            "get_reranker_provider",
            return_value=reranker,
        ),
    ):
        results = await hybrid_search_legal_chunks(
            db=None,
            query="What is the punishment for mob lynching?",
            additional_queries=[
                "group of five or more persons acting in concert "
                "commits murder"
            ],
            additional_query_weights=[1.0],
            rerank_query=(
                "What is the punishment for mob lynching?"
            ),
            top_k=2,
            candidate_k=2,
        )

    assert [chunk.id for chunk in results][0] == target.id
    assert vector_search.await_count == 2
    assert lexical_search.await_count == 2
    reranker.rerank.assert_awaited_once()

    semantic_query = (
        reranker.rerank.await_args.kwargs[
            "query"
        ]
    )

    assert "mob lynching" in semantic_query
    assert "acting in concert" in semantic_query


@pytest.mark.asyncio
async def test_low_confidence_model_expansions_cannot_overrule_primary_query():
    article_21 = make_chunk(
        21,
        "No person shall be deprived of life or personal liberty except "
        "according to procedure established by law.",
    )
    article_22 = make_chunk(
        22,
        "Protection against arrest and detention in certain cases.",
    )

    async def search_side_effect(*, query, **kwargs):
        if "arbitrary detention" in query or "detention" == query:
            return [article_22]
        return [article_21]

    reranker = AsyncMock()
    reranker.rerank.return_value = [article_22, article_21]

    with (
        patch(
            "app.services.hybrid_retrieval.search_legal_chunks",
            new_callable=AsyncMock,
            side_effect=search_side_effect,
        ),
        patch(
            "app.services.hybrid_retrieval.search_legal_chunks_lexical",
            new_callable=AsyncMock,
            side_effect=search_side_effect,
        ),
        patch(
            "app.services.hybrid_retrieval.get_reranker_provider",
            return_value=reranker,
        ),
    ):
        results = await hybrid_search_legal_chunks(
            db=None,
            query="life personal liberty procedure established by law",
            additional_queries=[
                "constitutional protection against arbitrary detention",
                "detention",
                "arbitrary detention",
            ],
            additional_query_weights=[0.25, 0.25, 0.25],
            top_k=1,
            candidate_k=2,
        )

    assert [chunk.id for chunk in results] == [21]
    semantic_query = reranker.rerank.await_args.kwargs["query"]
    assert "arbitrary detention" not in semantic_query


@pytest.mark.asyncio
async def test_primary_candidate_floor_survives_repeated_expansion_noise():
    article_21 = make_chunk(
        21,
        "No person shall be deprived of life or personal liberty except "
        "according to procedure established by law.",
    )
    article_22_chunks = [
        make_chunk(
            chunk_id,
            "Protection against arrest and preventive detention.",
        )
        for chunk_id in (2201, 2202, 2203)
    ]

    async def search_side_effect(*, query, **kwargs):
        if query.startswith("life personal liberty"):
            return [article_21, *article_22_chunks]
        return list(article_22_chunks)

    reranker = AsyncMock()
    reranker.rerank.return_value = [
        *article_22_chunks,
        article_21,
    ]

    with (
        patch(
            "app.services.hybrid_retrieval.search_legal_chunks",
            new_callable=AsyncMock,
            side_effect=search_side_effect,
        ),
        patch(
            "app.services.hybrid_retrieval.search_legal_chunks_lexical",
            new_callable=AsyncMock,
            side_effect=search_side_effect,
        ),
        patch(
            "app.services.hybrid_retrieval.get_reranker_provider",
            return_value=reranker,
        ),
    ):
        results = await hybrid_search_legal_chunks(
            db=None,
            query="life personal liberty procedure established by law",
            additional_queries=[
                "arbitrary detention",
                "preventive detention",
                "protection against detention",
            ],
            additional_query_weights=[0.25, 0.25, 0.25],
            top_k=2,
            candidate_k=4,
        )

    assert article_21.id in [chunk.id for chunk in results]


@pytest.mark.asyncio
async def test_additional_query_weights_must_align_with_queries():
    with pytest.raises(ValueError, match="must align"):
        await hybrid_search_legal_chunks(
            db=None,
            query="criminal intimidation",
            additional_queries=["threat of injury"],
            additional_query_weights=[],
        )


@pytest.mark.asyncio
async def test_duplicate_additional_queries_are_executed_once():
    chunk = make_chunk(20, "Test provision.")

    vector_search = AsyncMock(
        return_value=[chunk]
    )
    lexical_search = AsyncMock(
        return_value=[chunk]
    )
    reranker = AsyncMock()
    reranker.rerank.return_value = [chunk]

    with (
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks",
            vector_search,
        ),
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks_lexical",
            lexical_search,
        ),
        patch(
            "app.services.hybrid_retrieval."
            "get_reranker_provider",
            return_value=reranker,
        ),
    ):
        await hybrid_search_legal_chunks(
            db=None,
            query="criminal intimidation",
            additional_queries=[
                "Criminal Intimidation",
                "criminal intimidation ",
            ],
            top_k=1,
            candidate_k=1,
        )

    assert vector_search.await_count == 1
    assert lexical_search.await_count == 1


@pytest.mark.asyncio
async def test_empty_candidate_set_does_not_load_reranker():
    with (
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.hybrid_retrieval."
            "search_legal_chunks_lexical",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.hybrid_retrieval."
            "get_reranker_provider",
        ) as get_reranker,
    ):
        results = await hybrid_search_legal_chunks(
            db=None,
            query="unmatched legal concept",
            top_k=1,
            candidate_k=1,
        )

    assert results == []
    get_reranker.assert_not_called()
