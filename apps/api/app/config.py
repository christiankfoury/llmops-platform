from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="local", alias="ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+psycopg://ai_platform:local_dev_password@localhost:55432/ai_platform",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="API_CORS_ORIGINS",
    )
    otel_tracing_enabled: bool = Field(default=False, alias="OTEL_TRACING_ENABLED")
    otel_service_name: str = Field(default="production-ai-platform-api", alias="OTEL_SERVICE_NAME")
    otel_traces_exporter: str = Field(default="console", alias="OTEL_TRACES_EXPORTER")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(
        default=60,
        alias="RATE_LIMIT_REQUESTS_PER_MINUTE",
    )
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    provider_max_attempts: int = Field(default=2, alias="PROVIDER_MAX_ATTEMPTS")
    provider_retry_backoff_ms: int = Field(default=100, alias="PROVIDER_RETRY_BACKOFF_MS")
    provider_timeout_seconds: int = Field(default=15, alias="PROVIDER_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
