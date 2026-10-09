from datetime import datetime

from pydantic import BaseModel


class LegalEvidence(BaseModel):
    citation_id: str | None = None

    chunk_id: int
    content: str

    document_title: str | None = None
    document_type: str | None = None

    act_name: str | None = None
    act_short_name: str | None = None

    version_label: str | None = None

    section_number: str | None = None
    section_title: str | None = None

    subsection_number: str | None = None
    clause_number: str | None = None

    source_name: str | None = None
    source_publisher: str | None = None
    source_url: str | None = None

    publication_date: datetime | None = None
    retrieved_at: datetime | None = None

    citation_text: str | None = None

    is_verified: bool = False
