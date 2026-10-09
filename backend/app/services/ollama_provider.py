import httpx

from app.core.config import settings
from app.schemas.llm import (
    LLMRequest,
    LLMResponse,
)
from app.services.llm_provider import LLMProvider


class OllamaProvider(LLMProvider):

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        keep_alive: str | int | None = None,
        context_length: int | None = None,
    ):
        self.base_url = (
            base_url
            or settings.OLLAMA_BASE_URL
        ).rstrip("/")

        self.model = (
            model
            or settings.LLM_MODEL
        )

        self.keep_alive = (
            settings.OLLAMA_KEEP_ALIVE
            if keep_alive is None
            else keep_alive
        )

        self.context_length = (
            settings.OLLAMA_CONTEXT_LENGTH
            if context_length is None
            else context_length
        )

        if self.context_length <= 0:
            raise ValueError(
                "Ollama context length must be greater than 0."
            )

    async def _post_chat(
        self,
        payload: dict[str, object],
    ) -> dict:
        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )

            response.raise_for_status()

            return response.json()

    async def warm_up(self) -> None:
        """Preload the configured model without generating text."""

        await self._post_chat(
            {
                "model": self.model,
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {
                    "num_ctx": self.context_length,
                },
            }
        )

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "num_ctx": self.context_length,
            },
        }

        if request.response_schema is not None:
            payload["format"] = (
                request.response_schema
            )

        data = await self._post_chat(payload)

        message = data.get("message", {})

        return LLMResponse(
            content=message.get("content", ""),
            model=data.get(
                "model",
                self.model,
            ),
            provider="ollama",
            prompt_tokens=data.get(
                "prompt_eval_count"
            ),
            completion_tokens=data.get(
                "eval_count"
            ),
            finish_reason=data.get(
                "done_reason"
            ),
        )
