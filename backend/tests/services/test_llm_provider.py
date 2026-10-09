from unittest.mock import AsyncMock

import pytest

from app.schemas.llm import (
    LLMMessage,
    LLMRequest,
)
from app.services.ollama_provider import (
    OllamaProvider,
)


def test_ollama_provider_initialization():

    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="test-model",
    )

    assert (
        provider.base_url
        == "http://localhost:11434"
    )

    assert provider.model == "test-model"


def test_llm_request_schema():

    request = LLMRequest(
        messages=[
            LLMMessage(
                role="user",
                content="Hello",
            )
        ]
    )

    assert len(request.messages) == 1

    assert (
        request.messages[0].role
        == "user"
    )

    assert (
        request.messages[0].content
        == "Hello"
    )


def test_llm_request_defaults():

    request = LLMRequest(
        messages=[
            LLMMessage(
                role="user",
                content="Hello",
            )
        ]
    )

    assert request.temperature == 0.2
    assert request.max_tokens == 1000


@pytest.mark.asyncio
async def test_ollama_generation_sets_keep_alive():
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="test-model",
        keep_alive="30m",
    )

    provider._post_chat = AsyncMock(
        return_value={
            "model": "test-model",
            "message": {
                "content": "Test answer",
            },
            "done_reason": "stop",
        }
    )

    request = LLMRequest(
        messages=[
            LLMMessage(
                role="user",
                content="Hello",
            )
        ]
    )

    response = await provider.generate(request)

    payload = provider._post_chat.await_args.args[0]

    assert payload["keep_alive"] == "30m"
    assert payload["options"]["num_ctx"] == 8192
    assert response.content == "Test answer"


@pytest.mark.asyncio
async def test_ollama_warm_up_uses_empty_chat_request():
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="test-model",
        keep_alive="30m",
    )

    provider._post_chat = AsyncMock(
        return_value={
            "model": "test-model",
            "done": True,
        }
    )

    await provider.warm_up()

    provider._post_chat.assert_awaited_once_with(
        {
            "model": "test-model",
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "num_ctx": 8192,
            },
        }
    )
