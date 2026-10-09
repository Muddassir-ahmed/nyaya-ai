from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.emergency import (
    EmergencyAnalyzeRequest,
    EmergencyResponse,
)
from app.services.emergency_orchestrator import EmergencyOrchestrator


router = APIRouter(
    prefix="/emergency",
    tags=["Emergency"],
)


@router.post(
    "/analyze",
    response_model=EmergencyResponse,
)
async def analyze_emergency(
    payload: EmergencyAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> EmergencyResponse:
    """
    Analyze a user query for an emergency situation and return
    verified emergency information.

    The caller may optionally provide a trusted jurisdiction.

    Jurisdiction priority:

    1. Explicit jurisdiction supplied by the caller.
    2. Jurisdiction detected from the user's query.
    3. India as the national default.

    Emergency contacts are retrieved only from the verified
    emergency directory. Emergency numbers are never generated
    by an LLM.
    """

    orchestrator = EmergencyOrchestrator()

    return await orchestrator.handle(
        db=db,
        query=payload.query,
        jurisdiction=payload.jurisdiction,
    )