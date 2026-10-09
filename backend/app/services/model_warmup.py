import logging

from app.services.llm_factory import get_llm_provider
from app.services.ollama_provider import OllamaProvider
from app.services.reranking import warm_up_reranker


logger = logging.getLogger(__name__)


async def warm_up_inference_models() -> dict[str, bool]:
    """
    Load local inference models before the first legal request.

    Warm-up failures are recorded and logged without preventing
    deterministic emergency, authority, civic, and health routes
    from starting.
    """

    status = {
        "reranker": False,
        "llm": False,
    }

    try:
        await warm_up_reranker()
        status["reranker"] = True
    except Exception:
        logger.exception(
            "Reranker warm-up failed; it will retry on first use."
        )

    try:
        provider = get_llm_provider()

        if isinstance(provider, OllamaProvider):
            await provider.warm_up()

        status["llm"] = True
    except Exception:
        logger.exception(
            "LLM warm-up failed; it will retry on first use."
        )

    return status
