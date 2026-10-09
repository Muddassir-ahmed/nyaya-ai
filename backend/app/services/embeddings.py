from abc import ABC, abstractmethod

import httpx

from app.core.config import settings


class EmbeddingProvider(ABC):
    """Base interface for embedding providers."""

    @abstractmethod
    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        raise NotImplementedError


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using a locally running Ollama server."""

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.EMBEDDING_MODEL

        if not self.model:
            raise RuntimeError(
                "EMBEDDING_MODEL is not configured."
            )

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:

        embeddings = await self.embed_texts([text])

        if not embeddings:
            raise RuntimeError(
                "Ollama returned no embeddings."
            )

        return embeddings[0]

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": texts,
                },
            )

            response.raise_for_status()

            data = response.json()

        embeddings = data.get("embeddings")

        if not embeddings:
            raise RuntimeError(
                "Ollama returned no embeddings."
            )

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Ollama returned a different number of "
                "embeddings than input texts."
            )

        return embeddings


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "ollama":
        return OllamaEmbeddingProvider()

    raise ValueError(
        f"Unsupported embedding provider: {provider}"
    )