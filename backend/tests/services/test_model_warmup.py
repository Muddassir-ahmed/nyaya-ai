from unittest.mock import AsyncMock, Mock

import pytest

from app.services.model_warmup import (
    warm_up_inference_models,
)
from app.services.ollama_provider import OllamaProvider


@pytest.mark.asyncio
async def test_inference_models_are_warmed(
    monkeypatch,
):
    reranker_warm_up = AsyncMock()
    provider = Mock(spec=OllamaProvider)
    provider.warm_up = AsyncMock()

    monkeypatch.setattr(
        "app.services.model_warmup.warm_up_reranker",
        reranker_warm_up,
    )
    monkeypatch.setattr(
        "app.services.model_warmup.get_llm_provider",
        lambda: provider,
    )

    status = await warm_up_inference_models()

    reranker_warm_up.assert_awaited_once_with()
    provider.warm_up.assert_awaited_once_with()
    assert status == {
        "reranker": True,
        "llm": True,
    }


@pytest.mark.asyncio
async def test_warm_up_failure_does_not_block_other_models(
    monkeypatch,
):
    provider = Mock(spec=OllamaProvider)
    provider.warm_up = AsyncMock()

    monkeypatch.setattr(
        "app.services.model_warmup.warm_up_reranker",
        AsyncMock(side_effect=RuntimeError("test failure")),
    )
    monkeypatch.setattr(
        "app.services.model_warmup.get_llm_provider",
        lambda: provider,
    )

    status = await warm_up_inference_models()

    provider.warm_up.assert_awaited_once_with()
    assert status == {
        "reranker": False,
        "llm": True,
    }
