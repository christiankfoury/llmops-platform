from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Production AI Platform API",
    version="0.1.0",
    description="Local development foundation for the LLMOps gateway.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ready",
        "environment": settings.environment,
        "database": "configured" if settings.database_url else "missing",
        "redis": "configured" if settings.redis_url else "missing",
    }
