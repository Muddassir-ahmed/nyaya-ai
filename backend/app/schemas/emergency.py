from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EmergencyType(str, Enum):
    POLICE = "police"
    FIRE = "fire"
    MEDICAL = "medical"
    WOMEN_SAFETY = "women_safety"
    CHILD_SAFETY = "child_safety"
    DISASTER = "disaster"
    CYBERCRIME = "cybercrime"
    OTHER = "other"


class EmergencyContact(BaseModel):
    name: str
    emergency_type: EmergencyType
    phone_number: str
    jurisdiction: str

    primary_source_name: str
    primary_source_url: str

    secondary_source_name: str | None = None
    secondary_source_url: str | None = None

    is_verified: bool = False
    is_active: bool = True
    verified_at: datetime | None = None
    verification_notes: str | None = None

class EmergencyAnalyzeRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User-described emergency or safety situation.",
    )

    jurisdiction: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Optional trusted jurisdiction supplied by the caller. "
            "If omitted, NyayaAI may detect jurisdiction from the query."
        ),
    )


class EmergencyResponse(BaseModel):
    is_emergency: bool
    emergency_type: EmergencyType | None = None

    immediate_actions: list[str] = Field(default_factory=list)

    contacts: list[EmergencyContact] = Field(
        default_factory=list
    )

    safety_warning: str | None = None
    verification_note: str | None = None
