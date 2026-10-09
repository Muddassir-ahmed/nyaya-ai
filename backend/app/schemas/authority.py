from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AuthorityType(str, Enum):
    POLICE = "police"
    CYBERCRIME = "cybercrime"
    CONSUMER = "consumer"
    LABOUR = "labour"
    TRANSPORT = "transport"
    REVENUE_LAND = "revenue_land"
    MUNICIPAL = "municipal"
    DISTRICT_ADMINISTRATION = "district_administration"
    LEGAL_SERVICES = "legal_services"
    OTHER = "other"


class AuthorityRecord(BaseModel):
    id: int

    name: str
    authority_type: AuthorityType
    domain: str

    service_key: str
    service_name: str
    description: str | None = None

    jurisdiction_id: int
    jurisdiction_name: str
    jurisdiction_code: str

    official_portal_url: str | None = None
    complaint_url: str | None = None

    phone_number: str | None = None
    email: str | None = None

    primary_source_name: str
    primary_source_url: str

    secondary_source_name: str | None = None
    secondary_source_url: str | None = None

    is_verified: bool
    verified_at: datetime | None = None

    verification_notes: str | None = None
    is_active: bool = True


class AuthorityResponse(BaseModel):
    service_key: str

    jurisdiction: str | None = None

    authorities: list[AuthorityRecord] = Field(
        default_factory=list
    )

    verification_note: str | None = None