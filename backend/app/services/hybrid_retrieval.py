from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_chunk import LegalChunk
from app.services.lexical_retrieval import (
    search_legal_chunks_lexical,
)
from app.services.reranking import (
    get_reranker_provider,
)
from app.services.retrieval import (
    search_legal_chunks,
)


RRF_K = 60
DEFAULT_EXPANSION_WEIGHT = 0.9
RERANK_CONTEXT_WEIGHT_THRESHOLD = 0.5
PRIMARY_CANDIDATE_FLOOR_LIMIT = 2


def _select_with_reserves(
    *,
    ranked_ids: list[int],
    reserve_ids: list[int],
    limit: int,
) -> list[int]:
    """Select the best IDs while retaining bounded primary evidence."""

    reserves: list[int] = []
    seen_reserves: set[int] = set()

    for chunk_id in reserve_ids:
        if chunk_id in seen_reserves:
            continue
        seen_reserves.add(chunk_id)
        reserves.append(chunk_id)
        if len(reserves) == min(
            PRIMARY_CANDIDATE_FLOOR_LIMIT,
            limit,
        ):
            break

    reserve_set = set(reserves)
    selected = [
        chunk_id
        for chunk_id in ranked_ids
        if chunk_id not in reserve_set
    ][: max(0, limit - len(reserves))]
    selected.extend(reserves)

    rank_positions = {
        chunk_id: position
        for position, chunk_id in enumerate(ranked_ids)
    }
    return sorted(
        selected,
        key=rank_positions.__getitem__,
    )


async def hybrid_search_legal_chunks(
    db: AsyncSession,
    query: str,
    additional_queries: list[str] | None = None,
    additional_query_weights: list[float] | None = None,
    rerank_query: str | None = None,
    top_k: int = 5,
    candidate_k: int = 20,
    act_id: int | None = None,
    version_id: int | None = None,
    jurisdiction_id: int | None = None,
    source_id: int | None = None,
    effective_date: date | None = None,
) -> list[LegalChunk]:

    if not query.strip():
        raise ValueError("Query cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    if candidate_k < top_k:
        raise ValueError(
            "candidate_k must be greater than or equal to top_k."
        )

    raw_additional_queries = additional_queries or []

    if (
        additional_query_weights is not None
        and len(additional_query_weights)
        != len(raw_additional_queries)
    ):
        raise ValueError(
            "additional_query_weights must align with "
            "additional_queries."
        )

    resolved_additional_weights = (
        additional_query_weights
        if additional_query_weights is not None
        else [
            DEFAULT_EXPANSION_WEIGHT
            for _ in raw_additional_queries
        ]
    )

    weighted_inputs = [
        (query, 1.0),
        *zip(
            raw_additional_queries,
            resolved_additional_weights,
        ),
    ]

    queries: list[tuple[str, float]] = []
    seen_queries: set[str] = set()

    for raw_query, query_weight in weighted_inputs:
        if not 0.0 < query_weight <= 1.0:
            raise ValueError(
                "Query weights must be greater than 0 and at most 1."
            )

        normalized_query = " ".join(
            raw_query.split()
        ).strip()

        if not normalized_query:
            continue

        query_key = normalized_query.casefold()

        if query_key in seen_queries:
            continue

        seen_queries.add(query_key)
        queries.append((normalized_query, query_weight))

        # Bound query fan-out and latency.  The query planner itself
        # is also limited, but this protects every direct caller.
        if len(queries) == 5:
            break

    scores: dict[int, float] = {}
    chunks_by_id: dict[int, LegalChunk] = {}
    primary_scores: dict[int, float] = {}

    for query_index, (search_query, query_weight) in enumerate(queries):
        vector_results = await search_legal_chunks(
            db=db,
            query=search_query,
            top_k=candidate_k,
            act_id=act_id,
            version_id=version_id,
            jurisdiction_id=jurisdiction_id,
            source_id=source_id,
            effective_date=effective_date,
        )

        lexical_results = await search_legal_chunks_lexical(
            db=db,
            query=search_query,
            top_k=candidate_k,
            act_id=act_id,
            version_id=version_id,
            jurisdiction_id=jurisdiction_id,
            source_id=source_id,
            effective_date=effective_date,
        )

        for rank, chunk in enumerate(
            vector_results,
            start=1,
        ):
            contribution = query_weight / (RRF_K + rank)
            scores[chunk.id] = scores.get(chunk.id, 0.0) + contribution

            if query_index == 0:
                primary_scores[chunk.id] = (
                    primary_scores.get(chunk.id, 0.0)
                    + contribution
                )

            chunks_by_id[chunk.id] = chunk

        for rank, chunk in enumerate(
            lexical_results,
            start=1,
        ):
            contribution = query_weight / (RRF_K + rank)
            scores[chunk.id] = scores.get(chunk.id, 0.0) + contribution

            if query_index == 0:
                primary_scores[chunk.id] = (
                    primary_scores.get(chunk.id, 0.0)
                    + contribution
                )

            chunks_by_id[chunk.id] = chunk

    ranked_ids = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )

    primary_ranked_ids = sorted(
        primary_scores,
        key=primary_scores.get,
        reverse=True,
    )

    candidate_ids = _select_with_reserves(
        ranked_ids=ranked_ids,
        reserve_ids=primary_ranked_ids,
        limit=candidate_k,
    )

    candidates = [
        chunks_by_id[chunk_id]
        for chunk_id in candidate_ids
    ]

    if not candidates:
        return []

    reranker = get_reranker_provider()

    # ---------------------------------------------------------
    # Semantic reranking is an additional ranking signal.
    #
    # Vector + lexical retrieval have already contributed
    # reciprocal-rank scores above. Do not allow the semantic
    # reranker to completely replace that evidence.
    #
    # Rerank the full candidate set, then add its reciprocal
    # rank as a third signal.
    # ---------------------------------------------------------
    semantic_query = (
        rerank_query.strip()
        if rerank_query
        and rerank_query.strip()
        else query
    )

    rerank_concepts = [
        search_query
        for search_query, query_weight in queries[1:]
        if query_weight >= RERANK_CONTEXT_WEIGHT_THRESHOLD
    ]

    if rerank_concepts:
        semantic_query = (
            f"{semantic_query}\n"
            "Related legal search concepts: "
            + "; ".join(rerank_concepts)
        )[:1200]

    semantic_results = await reranker.rerank(
        query=semantic_query,
        chunks=candidates,
        top_k=len(candidates),
    )

    semantic_ranks = {
        chunk.id: rank
        for rank, chunk in enumerate(
            semantic_results,
            start=1,
        )
    }

    missing_semantic_rank = len(candidates) + 1

    for chunk in candidates:
        semantic_rank = semantic_ranks.get(
            chunk.id,
            missing_semantic_rank,
        )

        scores[chunk.id] = (
            scores.get(
                chunk.id,
                0.0,
            )
            + (
                1.0
                / (
                    RRF_K
                    + semantic_rank
                )
            )
        )

    final_ids = sorted(
        (chunk.id for chunk in candidates),
        key=lambda chunk_id: (
            scores[chunk_id],
            -ranked_ids.index(chunk_id),
        ),
        reverse=True,
    )

    selected_ids = _select_with_reserves(
        ranked_ids=final_ids,
        reserve_ids=primary_ranked_ids,
        limit=top_k,
    )

    return [
        chunks_by_id[chunk_id]
        for chunk_id in selected_ids
    ]
