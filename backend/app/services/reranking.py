from abc import ABC, abstractmethod
import asyncio
from functools import lru_cache
import math
import re
from typing import Any

from app.core.config import settings
from app.models.legal_chunk import LegalChunk


class RerankerProvider(ABC):
    async def warm_up(self) -> None:
        """Load provider resources before the first query."""

        return None

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: list[LegalChunk],
        top_k: int = 5,
    ) -> list[LegalChunk]:
        raise NotImplementedError


class KeywordReranker(RerankerProvider):
    """
    Lightweight lexical reranker.

    This remains available as a fallback/baseline.
    """

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(
            re.findall(
                r"\b[a-zA-Z0-9]+\b",
                text.lower(),
            )
        )

    @staticmethod
    def _score(
        query_tokens: set[str],
        content_tokens: set[str],
    ) -> float:

        if not query_tokens or not content_tokens:
            return 0.0

        overlap = query_tokens.intersection(
            content_tokens
        )

        return len(overlap) / math.sqrt(
            len(query_tokens)
            * len(content_tokens)
        )

    async def rerank(
        self,
        query: str,
        chunks: list[LegalChunk],
        top_k: int = 5,
    ) -> list[LegalChunk]:

        if not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        if not chunks:
            return []

        query_tokens = self._tokenize(query)

        scored_chunks = []

        for original_rank, chunk in enumerate(
            chunks,
            start=1,
        ):
            content_tokens = self._tokenize(
                chunk.content
            )

            score = self._score(
                query_tokens,
                content_tokens,
            )

            scored_chunks.append(
                (
                    score,
                    original_rank,
                    chunk,
                )
            )

        scored_chunks.sort(
            key=lambda item: (
                item[0],
                -item[1],
            ),
            reverse=True,
        )

        return [
            chunk
            for _, _, chunk
            in scored_chunks[:top_k]
        ]


class SemanticReranker(RerankerProvider):
    """
    Local Cross-Encoder semantic reranker.

    The model receives pairs:

        (query, legal_chunk)

    and produces a relevance score for each pair.
    """

    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int | None = None,
        max_length: int | None = None,
    ) -> None:

        self.model_name = (
            model_name
            if model_name is not None
            else settings.RERANKER_MODEL
        )

        if not self.model_name:
            raise RuntimeError(
                "RERANKER_MODEL is not configured."
            )

        self.batch_size = (
            batch_size
            if batch_size is not None
            else settings.RERANKER_BATCH_SIZE
        )

        self.max_length = (
            max_length
            if max_length is not None
            else settings.RERANKER_MAX_LENGTH
        )

        self._model: Any | None = None

    async def warm_up(self) -> None:
        """Load the CrossEncoder outside the first request."""

        await asyncio.to_thread(self._load_model)

    def _load_model(self) -> Any:

        if self._model is None:

            from sentence_transformers import (
                CrossEncoder,
            )

            print(
                f"Loading reranker model: "
                f"{self.model_name}"
            )

            self._model = CrossEncoder(
                self.model_name,
                max_length=self.max_length,
            )

            print(
                "Reranker model loaded."
            )

        return self._model

    def _predict(
        self,
        query: str,
        chunks: list[LegalChunk],
    ) -> list[float]:

        model = self._load_model()

        pairs = [
            [
                query,
                chunk.content,
            ]
            for chunk in chunks
        ]

        scores = model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        return [
            float(score)
            for score in scores
        ]

    async def rerank(
        self,
        query: str,
        chunks: list[LegalChunk],
        top_k: int = 5,
    ) -> list[LegalChunk]:

        if not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        if not chunks:
            return []

        scores = await asyncio.to_thread(
            self._predict,
            query,
            chunks,
        )

        scored_chunks = list(
            zip(
                scores,
                chunks,
            )
        )

        scored_chunks.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            chunk
            for _, chunk
            in scored_chunks[:top_k]
        ]


@lru_cache(maxsize=4)
def _get_semantic_reranker(
    model_name: str,
    batch_size: int,
    max_length: int,
) -> SemanticReranker:
    """
    Reuse the expensive semantic reranker for the same
    model configuration.

    The CrossEncoder itself remains lazily loaded by
    SemanticReranker._load_model().
    """

    return SemanticReranker(
        model_name=model_name,
        batch_size=batch_size,
        max_length=max_length,
    )


@lru_cache(maxsize=1)
def _get_keyword_reranker() -> KeywordReranker:
    return KeywordReranker()


def get_reranker_provider() -> RerankerProvider:

    provider = (
        settings.RERANKER_PROVIDER
        .lower()
        .strip()
    )

    if provider == "semantic":
        return _get_semantic_reranker(
            model_name=settings.RERANKER_MODEL,
            batch_size=settings.RERANKER_BATCH_SIZE,
            max_length=settings.RERANKER_MAX_LENGTH,
        )

    if provider == "keyword":
        return _get_keyword_reranker()

    raise ValueError(
        "Unsupported reranker provider: "
        f"{settings.RERANKER_PROVIDER}"
    )


async def warm_up_reranker() -> None:
    """Warm the configured cached reranker provider."""

    reranker = get_reranker_provider()
    await reranker.warm_up()
