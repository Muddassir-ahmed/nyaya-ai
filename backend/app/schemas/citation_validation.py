from pydantic import BaseModel, Field


class CitationValidationResult(BaseModel):
    is_valid: bool
    citation_completeness: float = Field(ge=0.0, le=1.0)

    valid_citations: list[str] = Field(default_factory=list)
    invalid_citations: list[str] = Field(default_factory=list)

    unsupported_claims: list[str] = Field(default_factory=list)

    validation_reasons: list[str] = Field(default_factory=list)