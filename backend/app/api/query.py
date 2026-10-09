from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.query import (
    QueryRequest,
    QueryResponse,
    QueryValidationSummary,
)
from app.services.query_orchestrator import (
    QueryOrchestrator,
    get_query_orchestrator,
)


router = APIRouter(
    tags=["Query"],
)


@router.post(
    "/query",
    response_model=QueryResponse,
)
async def process_query(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: QueryOrchestrator = Depends(
        get_query_orchestrator
    ),
) -> QueryResponse:
    """
    Main NyayaAI query endpoint.

    Routes a user's situation through the appropriate pipeline.

    Emergency situations are short-circuited to the verified
    emergency pipeline before normal legal RAG is performed.

    Non-emergency legal queries may proceed through retrieval,
    evidence verification, grounded answer generation,
    citation validation, claim validation, and
    answer-integrity validation.
    """

    result = await orchestrator.handle(
        db=db,
        query=payload.query,
        jurisdiction=payload.jurisdiction,
    )

    validation = None

    if (
        result.citation_validation is not None
        or result.claim_validation is not None
        or result.answer_integrity is not None
    ):
        validation = QueryValidationSummary(
            citation_valid=(
                result.citation_validation.is_valid
                if result.citation_validation is not None
                else None
            ),
            claim_grounding_valid=(
                result.claim_validation.is_valid
                if result.claim_validation is not None
                else None
            ),
            answer_integrity_valid=(
                result.answer_integrity.is_valid
                if result.answer_integrity is not None
                else None
            ),
            citation_completeness=(
                result.citation_validation.citation_completeness
                if result.citation_validation is not None
                else None
            ),
        )

    return QueryResponse(
        route=result.route,
        analysis=result.analysis,
        emergency_response=result.emergency_response,
        authority_response=result.authority_response,
        legal_answer=result.legal_answer,
        evidence=result.evidence,
        validation=validation,
        retrieval_performed=result.retrieval_performed,
        routing_reason=result.routing_reason,
        answer_blocked=result.answer_blocked,
        safety_reason=result.safety_reason,
        follow_up_question=result.follow_up_question,
    )