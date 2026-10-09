from app.core.config import settings
from app.services.llm_provider import LLMProvider
from app.services.ollama_provider import OllamaProvider


def get_llm_provider() -> LLMProvider:

    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        return OllamaProvider()

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )