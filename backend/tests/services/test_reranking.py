from unittest.mock import Mock

import pytest

from app.core.config import settings
from app.services.reranking import (
    SemanticReranker,
    get_reranker_provider,
)


def test_semantic_reranker_provider_is_reused(
    monkeypatch,
):
    """
    The semantic reranker is expensive because its
    CrossEncoder model is loaded lazily into the provider.

    Repeated provider lookups for the same configuration
    must therefore return the same provider instance.
    """

    monkeypatch.setattr(
        settings,
        "RERANKER_PROVIDER",
        "semantic",
    )

    first = get_reranker_provider()
    second = get_reranker_provider()

    assert isinstance(
        first,
        SemanticReranker,
    )

    assert first is second

def test_semantic_reranker_cache_respects_configuration(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "RERANKER_PROVIDER",
        "semantic",
    )

    monkeypatch.setattr(
        settings,
        "RERANKER_MODEL",
        "test-model-a",
    )

    monkeypatch.setattr(
        settings,
        "RERANKER_BATCH_SIZE",
        8,
    )

    monkeypatch.setattr(
        settings,
        "RERANKER_MAX_LENGTH",
        512,
    )

    first = get_reranker_provider()

    # Changing only batch size must create
    # a different cached provider.
    monkeypatch.setattr(
        settings,
        "RERANKER_BATCH_SIZE",
        16,
    )

    second = get_reranker_provider()

    assert first is not second

    assert first.batch_size == 8
    assert second.batch_size == 16

    # Changing only max length must also
    # produce a different provider.
    monkeypatch.setattr(
        settings,
        "RERANKER_MAX_LENGTH",
        1024,
    )

    third = get_reranker_provider()

    assert second is not third

    assert second.max_length == 512
    assert third.max_length == 1024

    # Model name is part of the cache key too.
    monkeypatch.setattr(
        settings,
        "RERANKER_MODEL",
        "test-model-b",
    )

    fourth = get_reranker_provider()

    assert third is not fourth

    assert third.model_name == "test-model-a"
    assert fourth.model_name == "test-model-b"


@pytest.mark.asyncio
async def test_semantic_reranker_can_be_warmed_before_reranking(
    monkeypatch,
):
    reranker = SemanticReranker(
        model_name="test-model",
    )

    loader = Mock()

    monkeypatch.setattr(
        reranker,
        "_load_model",
        loader,
    )

    await reranker.warm_up()

    loader.assert_called_once_with()
