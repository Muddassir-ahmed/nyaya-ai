from pydantic import BaseModel, Field


class LegalAnswer(BaseModel):
    summary: str

    legal_basis: list[str] = Field(
        default_factory=list
    )

    possible_options: list[str] = Field(
        default_factory=list
    )

    evidence_to_preserve: list[str] = Field(
        default_factory=list
    )

    next_steps: list[str] = Field(
        default_factory=list
    )

    caveats: list[str] = Field(
        default_factory=list
    )

    citations: list[str] = Field(
        default_factory=list
    )