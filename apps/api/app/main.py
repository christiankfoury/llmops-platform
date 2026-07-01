import logging
import uuid
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.admin import router as admin_router
from app.api.gateway import router as gateway_router
from app.api.usage import router as usage_router
from app.config import get_settings
from app.observability.correlation import reset_request_id, set_request_id
from app.observability.logging import configure_logging
from app.observability.metrics import initialize_metrics, metrics_response, record_http_request
from app.observability.tracing import configure_tracing, get_tracer, set_span_attributes

settings = get_settings()
configure_logging()
logger = logging.getLogger("app.request")

_is_shutting_down = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_shutting_down
    _is_shutting_down = False
    yield
    _is_shutting_down = True
    logger.info("shutdown_started")


app = FastAPI(
    title="Production AI Platform API",
    version="0.1.0",
    description="Local development foundation for the LLMOps gateway.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

configure_tracing(app, settings)
initialize_metrics(settings.environment)

app.include_router(gateway_router)
app.include_router(usage_router)
app.include_router(admin_router)

tracer = get_tracer()


@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or f"http_{uuid.uuid4().hex}"
    token = set_request_id(request_id)
    started_at = perf_counter()
    status_code = 500
    trace_id = None

    try:
        with tracer.start_as_current_span("api.request") as span:
            span_context = span.get_span_context()
            if span_context.is_valid:
                trace_id = f"{span_context.trace_id:032x}"
            set_span_attributes(
                span,
                {
                    "http.request_id": request_id,
                    "http.method": request.method,
                    "http.route": request.url.path,
                    "deployment.environment": settings.environment,
                },
            )
            response = await call_next(request)
            status_code = response.status_code
            span.set_attribute("http.status_code", status_code)
            response.headers["X-Request-ID"] = request_id
            return response
    finally:
        latency_ms = max(1, int((perf_counter() - started_at) * 1000))
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "http_method": request.method,
                "http_path": request.url.path,
                "status_code": status_code,
                "latency_ms": latency_ms,
            },
        )
        route = request.scope.get("route")
        path = getattr(route, "path", None) or "unmatched"
        record_http_request(request.method, path, status_code, latency_ms)
        reset_request_id(token)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    if _is_shutting_down:
        raise HTTPException(status_code=503, detail="shutting down")

    settings = get_settings()
    return {
        "status": "ready",
        "environment": settings.environment,
        "database": "configured" if settings.database_url else "missing",
        "redis": "configured" if settings.redis_url else "missing",
    }


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return metrics_response()
