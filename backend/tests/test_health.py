from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.main import app, lifespan


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "nyaya-ai"


@pytest.mark.asyncio
async def test_lifespan_warms_inference_models(
    monkeypatch,
):
    warm_up = AsyncMock(
        return_value={
            "reranker": True,
            "llm": True,
        }
    )

    monkeypatch.setattr(
        settings,
        "PRELOAD_INFERENCE_MODELS",
        True,
    )
    monkeypatch.setattr(
        "app.main.warm_up_inference_models",
        warm_up,
    )

    async with lifespan(app):
        pass

    warm_up.assert_awaited_once_with()
