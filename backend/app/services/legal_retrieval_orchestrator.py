from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.query_analysis import (
    LegalDomain,
    LegalIntent,
    QueryAnalysis,
)
from app.services.hybrid_retrieval import (
    hybrid_search_legal_chunks,
)
from app.services.query_analyzer import (
    get_query_analyzer,
)
from app.services.constitution_reference import (
    get_constitution_context,
    resolve_constitution_article,
    resolve_constitution_preamble,
)
from app.services.legal_corpus_context import (
    get_bns_context,
    has_explicit_bns_reference,
)
from app.services.legal_query_planner import (
    LegalQueryPlanner,
    deterministic_legal_bridges,
    get_legal_query_planner,
)
from app.services.legal_evidence_focus import (
    focus_legal_chunks,
)
from app.models.legal_chunk import LegalChunk


@dataclass
class LegalRetrievalResult:
    analysis: QueryAnalysis
    chunks: list[LegalChunk]
    retrieval_query: str
    retrieval_performed: bool
    retrieval_queries: list[str] = field(
        default_factory=list
    )
    retrieval_reason: str | None = None

    user_jurisdiction: str | None = None
    legal_jurisdiction: str | None = None

    exact_reference: str | None = None
    exact_reference_status: str | None = None


@dataclass(frozen=True)
class RetrievalQuerySignals:
    queries: list[str]
    weights: list[float]
    focus_queries: list[str]


class LegalRetrievalOrchestrator:

    ANALYZER_REWRITE_WEIGHT = 0.75
    MODEL_EXPANSION_WEIGHT = 0.25

    RETRIEVAL_INTENTS = {
        LegalIntent.LEGAL_INFORMATION,
        LegalIntent.LEGAL_PROCEDURE,
        LegalIntent.COMPLAINT_GUIDANCE,
        LegalIntent.DOCUMENT_GUIDANCE,
    }

    NON_RAG_INTENTS = {
        LegalIntent.EMERGENCY,
        LegalIntent.AUTHORITY_LOOKUP,
        LegalIntent.GENERAL_CIVIC,
        LegalIntent.OUT_OF_SCOPE,
    }

    def __init__(
        self,
        query_planner: LegalQueryPlanner | None = None,
    ) -> None:
        self.query_planner = (
            query_planner
            or get_legal_query_planner()
        )

    @staticmethod
    def _prepare_retrieval_queries(
        analysis: QueryAnalysis,
        planned_queries: list[str],
        deterministic_queries: list[str],
    ) -> RetrievalQuerySignals:
        analyzer_queries = (
            analysis.rewritten_queries
            or [analysis.original_query]
        )

        primary_query = analyzer_queries[0]
        normalized_original = " ".join(
            analysis.original_query.split()
        ).strip()

        ordered_queries: list[tuple[str, float, bool]] = [
            (primary_query, 1.0, True)
        ]

        if (
            normalized_original.casefold()
            != primary_query.casefold()
        ):
            ordered_queries.append(
                (normalized_original, 1.0, True)
            )

        ordered_queries.extend(
            (query, 1.0, True)
            for query in deterministic_queries
        )
        ordered_queries.extend(
            (
                query,
                LegalRetrievalOrchestrator.ANALYZER_REWRITE_WEIGHT,
                True,
            )
            for query in analyzer_queries[1:]
        )

        deterministic_keys = {
            " ".join(query.split()).strip().casefold()
            for query in deterministic_queries
        }
        ordered_queries.extend(
            (
                query,
                LegalRetrievalOrchestrator.MODEL_EXPANSION_WEIGHT,
                False,
            )
            for query in planned_queries
            if " ".join(query.split()).strip().casefold()
            not in deterministic_keys
        )

        merged: list[str] = []
        weights: list[float] = []
        focus_queries: list[str] = []
        seen: set[str] = set()

        for raw_query, weight, trusted_for_focus in ordered_queries:
            query = " ".join(
                raw_query.split()
            ).strip()

            if not query:
                continue

            key = query.casefold()

            if key in seen:
                continue

            seen.add(key)
            merged.append(query)
            weights.append(weight)

            if trusted_for_focus:
                focus_queries.append(query)

            if len(merged) == 5:
                break

        return RetrievalQuerySignals(
            queries=merged,
            weights=weights,
            focus_queries=focus_queries,
        )

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        candidate_k: int = 20,
        effective_date: date | None = None,
        analysis: QueryAnalysis | None = None,
    ) -> LegalRetrievalResult:

        if analysis is None:
            analyzer = get_query_analyzer()
            analysis = analyzer.analyze(query)

        # --------------------------------------------------
        # 1. Emergency queries must not enter normal RAG.
        # --------------------------------------------------

        if analysis.intent == LegalIntent.EMERGENCY:

            return LegalRetrievalResult(
                analysis=analysis,
                chunks=[],
                retrieval_query="",
                retrieval_performed=False,
                retrieval_reason=(
                    "Emergency query routed to the "
                    "safety/emergency pipeline."
                ),
            )

        # --------------------------------------------------
        # 2. Authority lookup will eventually use a
        #    structured authority directory.
        # --------------------------------------------------

        if analysis.intent == LegalIntent.AUTHORITY_LOOKUP:

            return LegalRetrievalResult(
                analysis=analysis,
                chunks=[],
                retrieval_query="",
                retrieval_performed=False,
                retrieval_reason=(
                    "Authority lookup routed to the "
                    "structured authority directory."
                ),
            )

        # --------------------------------------------------
        # 3. General civic queries will eventually use
        #    civic/government service retrieval.
        # --------------------------------------------------

        if analysis.intent == LegalIntent.GENERAL_CIVIC:

            return LegalRetrievalResult(
                analysis=analysis,
                chunks=[],
                retrieval_query="",
                retrieval_performed=False,
                retrieval_reason=(
                    "General civic query routed to the "
                    "civic service pipeline."
                ),
            )

        # --------------------------------------------------
        # 4. Out-of-scope queries should not enter legal RAG.
        # --------------------------------------------------

        if analysis.intent == LegalIntent.OUT_OF_SCOPE:

            return LegalRetrievalResult(
                analysis=analysis,
                chunks=[],
                retrieval_query="",
                retrieval_performed=False,
                retrieval_reason=(
                    "Query is outside the supported "
                    "legal/civic scope."
                ),
            )

        # --------------------------------------------------
        # 5. If the analyzer says jurisdiction is required
        #    but it is missing, stop before retrieval.
        # --------------------------------------------------

        if analysis.requires_follow_up:

            return LegalRetrievalResult(
                analysis=analysis,
                chunks=[],
                retrieval_query="",
                retrieval_performed=False,
                retrieval_reason=(
                    "Jurisdiction is required before "
                    "performing this retrieval."
                ),
            )

        # --------------------------------------------------
        # 6. Exact Constitution Article resolution.
        #
        # Explicit Article references should not depend on
        # semantic similarity.
        #
        # Examples:
        #   Article 21
        #   Article 21A
        #   Article 243-I
        #   Article 238
        #
        # If the Article exists, the structured hierarchy
        # is authoritative.
        # --------------------------------------------------

        exact_article = (
            await resolve_constitution_article(
                db=db,
                query=query,
                top_k=top_k,
            )
        )

        # Explicit Article reference found in query.
        if exact_article is not None:

            # ----------------------------------------------
            # Explicit Article syntax was found, but that
            # Article does not exist in the loaded
            # Constitution version.
            #
            # Do NOT semantic-search nearby Articles.
            # ----------------------------------------------

            if not exact_article.matched:
                requested = (
                    exact_article.requested_number
                    or "unknown"
                )

                reference = (
                    f"Article {requested}"
                )

                return LegalRetrievalResult(
                    analysis=analysis,
                    chunks=[],
                    retrieval_query=query,
                    retrieval_performed=True,
                    retrieval_reason=(
                        f"{reference} was not found "
                        "in the loaded authoritative "
                        "Constitution version."
                    ),
                    user_jurisdiction=(
                        analysis.jurisdiction
                    ),
                    legal_jurisdiction="IN",
                    exact_reference=reference,
                    exact_reference_status=(
                        "not_found"
                    ),
                )

            reference = (
                "Article "
                f"{exact_article.canonical_number}"
            )

            # ----------------------------------------------
            # Existing but officially omitted Article.
            # ----------------------------------------------

            if exact_article.is_omitted:
                return LegalRetrievalResult(
                    analysis=analysis,
                    chunks=[],
                    retrieval_query=query,
                    retrieval_performed=True,
                    retrieval_reason=(
                        f"{reference} is marked "
                        "as omitted in the "
                        "authoritative Constitution "
                        "version."
                    ),
                    user_jurisdiction=(
                        analysis.jurisdiction
                    ),
                    legal_jurisdiction="IN",
                    exact_reference=reference,
                    exact_reference_status=(
                        "omitted"
                    ),
                )

            # ----------------------------------------------
            # Active exact Article.
            # ----------------------------------------------

            return LegalRetrievalResult(
                analysis=analysis,
                chunks=(
                    exact_article.chunks
                ),
                retrieval_query=query,
                retrieval_performed=True,
                retrieval_reason=None,
                user_jurisdiction=(
                    analysis.jurisdiction
                ),
                legal_jurisdiction="IN",
                exact_reference=reference,
                exact_reference_status=(
                    "active"
                ),
            )

        # --------------------------------------------------
        # 7. Exact Constitution Preamble resolution.
        #
        # When the user explicitly asks about the
        # Constitution's Preamble, use the canonical
        # document-level Preamble chunk directly instead
        # of allowing hybrid retrieval to add unrelated
        # constitutional provisions.
        #
        # This is restricted to constitutional queries so
        # that another Act's "preamble" is not incorrectly
        # treated as the Constitution's Preamble.
        # --------------------------------------------------

        if (
            analysis.domain
            == LegalDomain.CONSTITUTIONAL
        ):
            exact_preamble = (
                await resolve_constitution_preamble(
                    db=db,
                    query=query,
                    top_k=top_k,
                )
            )

            if exact_preamble is not None:
                return LegalRetrievalResult(
                    analysis=analysis,
                    chunks=(
                        exact_preamble.chunks
                    ),
                    retrieval_query=query,
                    retrieval_performed=True,
                    retrieval_reason=None,
                    user_jurisdiction=(
                        analysis.jurisdiction
                    ),
                    legal_jurisdiction="IN",
                    exact_reference="Preamble",
                    exact_reference_status=(
                        "active"
                    ),
                )

        # --------------------------------------------------
        # 8. Legal retrieval.
        #
        #    QueryAnalyzer may place a concise canonical
        #    legal retrieval query first while preserving
        #    the user's original wording as another rewrite.
        # --------------------------------------------------

        planned_queries: list[str] = []
        deterministic_queries = (
            deterministic_legal_bridges(query)
        )
        requested_aspects = []

        if self.query_planner.should_expand(
            analysis
        ):
            query_plan = await self.query_planner.plan(
                user_query=query,
                analysis=analysis,
            )

            planned_queries = (
                query_plan.search_queries
            )
            requested_aspects = (
                query_plan.requested_aspects
            )

        query_signals = (
            self._prepare_retrieval_queries(
                analysis=analysis,
                planned_queries=planned_queries,
                deterministic_queries=deterministic_queries,
            )
        )
        retrieval_queries = query_signals.queries

        retrieval_query = retrieval_queries[0]

        # Expose the actual retrieval phrases through the existing
        # analysis object for diagnostics and API observability.
        analysis = analysis.model_copy(
            update={
                "rewritten_queries": retrieval_queries,
            }
        )

        # --------------------------------------------------
        # 9. Map jurisdiction code to the database ID.
        #
        #    For now, the retrieval layer only receives a
        #    jurisdiction ID when it can be resolved.
        # --------------------------------------------------

        # The jurisdiction detected from the user's query represents
        # the user's location/context, not necessarily the jurisdiction
        # of the legal source.

        user_jurisdiction = analysis.jurisdiction

        # Do not pass user jurisdiction directly into legal retrieval.
        #
        # Example:
        # User jurisdiction = Assam (AS)
        # BNS legal jurisdiction = India (IN)
        #
        # State-specific legal filtering will be introduced later
        # through explicit legal-jurisdiction resolution.

        jurisdiction_id = None

        legal_act_id = None
        legal_version_id = None
        legal_jurisdiction = None

        # Constitution queries should retrieve
        # only from the Constitution corpus.
        #
        # This prevents unrelated BNS chunks
        # from competing with constitutional
        # evidence.
        if (
            analysis.domain
            == LegalDomain.CONSTITUTIONAL
        ):
            constitution_context = (
                await get_constitution_context(
                    db
                )
            )

            legal_act_id = (
                constitution_context.act_id
            )

            legal_version_id = (
                constitution_context.version_id
            )

            legal_jurisdiction = "IN"

        # An explicit BNS reference is authoritative corpus scope.
        # Inferred planner hints are deliberately not used as filters,
        # because a mistaken inference must not hide relevant evidence.
        elif (
            db is not None
            and has_explicit_bns_reference(query)
        ):
            bns_context = await get_bns_context(
                db
            )

            legal_act_id = bns_context.act_id
            legal_version_id = (
                bns_context.version_id
            )
            legal_jurisdiction = (
                bns_context.legal_jurisdiction
            )

        # --------------------------------------------------
        # 10. Run hybrid retrieval.
        # --------------------------------------------------

        # Model-expanded scenario queries carry more interpretation
        # uncertainty than deterministic/canonical queries.  Preserve
        # one additional, still-validated evidence candidate only when
        # the planner produced usable expansions.  This is a bounded
        # recall buffer, not a change to evidence verification.
        retrieval_top_k = min(
            candidate_k,
            top_k + (1 if planned_queries else 0),
        )

        chunks = await hybrid_search_legal_chunks(
            db=db,
            query=retrieval_query,
            additional_queries=(
                retrieval_queries[1:]
            ),
            additional_query_weights=(
                query_signals.weights[1:]
            ),
            rerank_query=query,
            top_k=retrieval_top_k,
            candidate_k=candidate_k,
            act_id=legal_act_id,
            version_id=legal_version_id,
            jurisdiction_id=(
                jurisdiction_id
            ),
            effective_date=(
                effective_date
            ),
        )

        chunks = await focus_legal_chunks(
            db=db,
            user_query=query,
            retrieval_queries=query_signals.focus_queries,
            chunks=chunks,
            requested_aspects=requested_aspects,
        )

        return LegalRetrievalResult(
            analysis=analysis,
            chunks=chunks,
            retrieval_query=retrieval_query,
            retrieval_performed=True,
            retrieval_queries=retrieval_queries,
            retrieval_reason=None,
            user_jurisdiction=user_jurisdiction,
            legal_jurisdiction=legal_jurisdiction,
        )


def get_legal_retrieval_orchestrator() -> (
    LegalRetrievalOrchestrator
):
    return LegalRetrievalOrchestrator()
