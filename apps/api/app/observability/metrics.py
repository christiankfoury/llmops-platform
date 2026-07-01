from decimal import Decimal

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled by the API.",
    ["method", "path", "status_code"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
GATEWAY_REQUESTS = Counter(
    "llm_gateway_requests_total",
    "LLM gateway requests by selected route and result.",
    ["provider", "model", "environment", "status", "error_category"],
)
GATEWAY_ERRORS = Counter(
    "llm_gateway_errors_total",
    "LLM gateway failures by selected route and error category.",
    ["provider", "model", "environment", "error_category"],
)
GATEWAY_REQUEST_DURATION = Histogram(
    "llm_gateway_request_duration_seconds",
    "LLM gateway request duration in seconds.",
    ["provider", "model", "environment", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
GATEWAY_ESTIMATED_COST = Counter(
    "llm_gateway_estimated_cost_usd_total",
    "Estimated LLM cost in USD.",
    ["provider", "model", "environment"],
)
GATEWAY_TOKENS = Counter(
    "llm_gateway_tokens_total",
    "Estimated LLM token usage.",
    ["provider", "model", "environment", "token_type"],
)
GATEWAY_AUTH_FAILURES = Counter(
    "llm_gateway_api_key_auth_failures_total",
    "Gateway API key authentication failures.",
    ["environment"],
)
GATEWAY_RATE_LIMIT_REJECTIONS = Counter(
    "llm_gateway_rate_limit_rejections_total",
    "Gateway requests rejected by rate limits.",
)


def initialize_metrics(environment: str) -> None:
    GATEWAY_AUTH_FAILURES.labels(environment).inc(0)
    GATEWAY_REQUESTS.labels("unknown", "unknown", environment, "failed", "auth_failed").inc(0)
    GATEWAY_RATE_LIMIT_REJECTIONS.inc(0)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def record_http_request(method: str, path: str, status_code: int, latency_ms: int) -> None:
    labels = {
        "method": method,
        "path": path,
        "status_code": str(status_code),
    }
    HTTP_REQUESTS.labels(**labels).inc()
    HTTP_REQUEST_DURATION.labels(**labels).observe(latency_ms / 1000)


def record_gateway_auth_failure(environment: str) -> None:
    GATEWAY_AUTH_FAILURES.labels(environment).inc()
    GATEWAY_REQUESTS.labels("unknown", "unknown", environment, "failed", "auth_failed").inc()
    GATEWAY_ERRORS.labels("unknown", "unknown", environment, "auth_failed").inc()


def record_gateway_config_error(environment: str) -> None:
    GATEWAY_REQUESTS.labels("unknown", "unknown", environment, "failed", "config_error").inc()
    GATEWAY_ERRORS.labels("unknown", "unknown", environment, "config_error").inc()


def record_gateway_rate_limit_rejection() -> None:
    GATEWAY_RATE_LIMIT_REJECTIONS.inc()


def record_gateway_request(
    provider: str,
    model: str,
    environment: str,
    status: str,
    latency_ms: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    estimated_cost: Decimal | None = None,
    error_category: str | None = None,
) -> None:
    normalized_error = error_category or "none"
    GATEWAY_REQUESTS.labels(provider, model, environment, status, normalized_error).inc()
    GATEWAY_REQUEST_DURATION.labels(provider, model, environment, status).observe(latency_ms / 1000)

    if error_category:
        GATEWAY_ERRORS.labels(provider, model, environment, error_category).inc()

    if estimated_cost is not None:
        GATEWAY_ESTIMATED_COST.labels(provider, model, environment).inc(float(estimated_cost))

    if input_tokens is not None:
        GATEWAY_TOKENS.labels(provider, model, environment, "input").inc(input_tokens)

    if output_tokens is not None:
        GATEWAY_TOKENS.labels(provider, model, environment, "output").inc(output_tokens)
