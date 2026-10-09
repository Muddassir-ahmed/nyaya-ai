from contextlib import asynccontextmanager
import logging

from fastapi import Request
from fastapi import FastAPI
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.emergency import router as emergency_router
from app.api.query import router as query_router
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.core.logging import setup_logging
from app.core.exceptions import global_exception_handler
from app.core.middleware import RequestIDMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.core.security_headers import (
    SecurityHeadersMiddleware,
)
from app.db.session import AsyncSessionLocal
from app.services.model_warmup import (
    warm_up_inference_models,
)


setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.PRELOAD_INFERENCE_MODELS:
        status = await warm_up_inference_models()
        logger.info(
            "Inference warm-up completed: %s",
            status,
        )

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Indian Legal & Civic Assistance Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(emergency_router)
app.include_router(query_router)
@app.get("/health")
async def health_check(request: Request):

    rate_limit(
        request,
        max_requests=5,
        window_seconds=60,
    )

    return {
        "status": "healthy",
        "service": "nyaya-ai",
    }


@app.get("/health/db")
async def database_health_check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()

    return {
        "status": "healthy",
        "database": "connected",
        "result": value,
    }