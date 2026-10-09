from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.emergency import EmergencyResponse
from app.schemas.legal_answer import LegalAnswer
from app.schemas.legal_evidence import LegalEvidence
from app.schemas.query_analysis import QueryAnalysis
from app.schemas.authority import AuthorityResponse


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User-described legal, civic, or emergency situation.",
    )

    jurisdiction: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Optional trusted user jurisdiction supplied by the caller."
        ),
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Query cannot be empty.")

        return value

    @field_validator("jurisdiction")
    @classmethod
    def normalize_jurisdiction(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None


class QueryValidationSummary(BaseModel):
    citation_valid: bool | None = None
    claim_grounding_valid: bool | None = None
    answer_integrity_valid: bool | None = None

    citation_completeness: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class QueryResponse(BaseModel):
    route: Literal[
        "emergency",
        "legal",
        "follow_up",
        "authority",
        "civic",
        "out_of_scope",
        "non_rag",
    ]

    analysis: QueryAnalysis

    emergency_response: EmergencyResponse | None = None
    authority_response: AuthorityResponse | None = None
    legal_answer: LegalAnswer | None = None
    evidence: list[LegalEvidence] = Field(
        default_factory=list
    )

    validation: QueryValidationSummary | None = None

    retrieval_performed: bool = False
    routing_reason: str | None = None

    answer_blocked: bool = False
    safety_reason: str | None = None

    follow_up_question: str | None = None
