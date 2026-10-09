from pydantic import BaseModel, Field


class AnswerIntegrityIssue(BaseModel):
    code: str
    message: str

    claim: str | None = None
    citation_id: str | None = None


class AnswerIntegrityResult(BaseModel):
    is_valid: bool

    issues: list[AnswerIntegrityIssue] = Field(
        default_factory=list
    )