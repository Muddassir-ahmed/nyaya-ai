from enum import Enum

from pydantic import BaseModel, Field


class ClaimSupportLevel(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"


class ClaimValidation(BaseModel):
    claim: str
    citation_ids: list[str] = Field(default_factory=list)
    support_level: ClaimSupportLevel
    reason: str


class ClaimValidationResult(BaseModel):
    is_valid: bool
    claims: list[ClaimValidation] = Field(default_factory=list)
    supported_claims: list[str] = Field(default_factory=list)
    partially_supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    validation_reasons: list[str] = Field(default_factory=list)