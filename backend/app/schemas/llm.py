from typing import Any

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMRequest(BaseModel):
    messages: list[LLMMessage] = Field(
        min_length=1
    )

    temperature: float = 0.2
    max_tokens: int = 1000

    # Optional provider-agnostic JSON schema.
    #
    # Providers that support structured output
    # can use this to constrain generation.
    response_schema: dict[str, Any] | None = None


class LLMResponse(BaseModel):
    content: str

    model: str

    provider: str

    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    finish_reason: str | None = None