from pydantic import BaseModel


class CitationVerification(BaseModel):
    chunk_id: int

    is_valid: bool

    has_source: bool
    has_source_url: bool
    has_act: bool
    has_version: bool
    has_section: bool
    document_verified: bool

    citation_text: str | None = None

    verification_reason: str