from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "NyayaAI"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str
    TEST_DATABASE_URL: str = ""

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = ""

    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_KEEP_ALIVE: str = "30m"
    OLLAMA_CONTEXT_LENGTH: int = 8192

    PRELOAD_INFERENCE_MODELS: bool = True

    RERANKER_PROVIDER: str = "semantic"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANKER_BATCH_SIZE: int = 16
    RERANKER_MAX_LENGTH: int = 512

    LOG_LEVEL: str = "INFO"

    CORS_ORIGINS: str = "http://localhost:3000"

    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    MAX_REQUEST_BODY_SIZE: int = 1_000_000

    ENVIRONMENT: str = "development"

    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
