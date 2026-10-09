from enum import Enum

from pydantic import BaseModel, Field


class LegalIntent(str, Enum):
    LEGAL_INFORMATION = "legal_information"
    LEGAL_PROCEDURE = "legal_procedure"
    COMPLAINT_GUIDANCE = "complaint_guidance"
    AUTHORITY_LOOKUP = "authority_lookup"
    DOCUMENT_GUIDANCE = "document_guidance"
    EMERGENCY = "emergency"
    GENERAL_CIVIC = "general_civic"
    OUT_OF_SCOPE = "out_of_scope"


class LegalDomain(str, Enum):
    CRIMINAL = "criminal"
    CIVIL = "civil"
    PROPERTY = "property"
    EMPLOYMENT = "employment"
    CONSUMER = "consumer"
    CYBERCRIME = "cybercrime"
    TRAFFIC = "traffic"
    FAMILY = "family"
    CONSTITUTIONAL = "constitutional"
    GOVERNMENT_SERVICES = "government_services"
    UNKNOWN = "unknown"


class UrgencyLevel(str, Enum):
    NORMAL = "normal"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class QueryAnalysis(BaseModel):
    original_query: str = Field(min_length=1)

    intent: LegalIntent

    domain: LegalDomain

    jurisdiction: str | None = None

    urgency: UrgencyLevel = UrgencyLevel.NORMAL

    keywords: list[str] = Field(default_factory=list)

    rewritten_queries: list[str] = Field(
        default_factory=list
    )

    requires_follow_up: bool = False

    missing_information: list[str] = Field(
        default_factory=list
    )