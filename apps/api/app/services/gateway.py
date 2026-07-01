import uuid
from decimal import Decimal
from time import perf_counter, sleep

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApiKey, Application, CostRecord, GatewayRequest, ModelRoute, PromptVersion
from app.observability.metrics import record_gateway_request
from app.observability.tracing import get_tracer, set_span_attributes
from app.schemas.gateway import CompletionRequest, CompletionResponse
from app.services.auth import hash_api_key
from app.services.mock_provider import (
    MockProviderError,
    MockProviderResult,
    MockProviderTimeout,
    complete_with_mock_provider,
)
from app.services.pricing import calculate_estimated_cost

tracer = get_tracer()


class GatewayAuthError(Exception):
    pass


class GatewayConfigError(Exception):
    pass


class GatewayProviderError(Exception):
    def __init__(self, message: str, status_code: int, error_category: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_category = error_category


def _elapsed_ms(started_at: float) -> int:
    return max(1, int((perf_counter() - started_at) * 1000))


def _resolve_api_key(db: Session, api_key_value: str) -> ApiKey:
    api_key = db.scalar(
        select(ApiKey).where(
            ApiKey.key_hash == hash_api_key(api_key_value),
            ApiKey.is_active.is_(True),
            ApiKey.revoked_at.is_(None),
        )
    )
    if api_key is None:
        raise GatewayAuthError("Invalid API key")
    return api_key


def _resolve_application(db: Session, api_key: ApiKey) -> Application:
    application = db.get(Application, api_key.application_id)
    if application is None or not application.is_active:
        raise GatewayAuthError("API key is not attached to an active application")
    return application


def _resolve_prompt(
    db: Session,
    application: Application,
    prompt_name: str,
) -> PromptVersion:
    prompt = db.scalar(
        select(PromptVersion)
        .where(
            PromptVersion.project_id == application.project_id,
            PromptVersion.application_id == application.id,
            PromptVersion.name == prompt_name,
            PromptVersion.is_active.is_(True),
        )
        .order_by(PromptVersion.version.desc())
    )
    if prompt is None:
        raise GatewayConfigError("No active prompt version found")
    return prompt


def _resolve_route(
    db: Session,
    application: Application,
    environment: str,
) -> ModelRoute:
    route = db.scalar(
        select(ModelRoute)
        .where(
            ModelRoute.project_id == application.project_id,
            ModelRoute.application_id == application.id,
            ModelRoute.environment == environment,
            ModelRoute.is_active.is_(True),
        )
        .order_by(ModelRoute.is_default.desc(), ModelRoute.priority.asc())
    )
    if route is None:
        raise GatewayConfigError("No active model route found")
    return route


def process_completion(
    db: Session,
    api_key_value: str,
    payload: CompletionRequest,
) -> CompletionResponse:
    started_at = perf_counter()
    with tracer.start_as_current_span("gateway.request") as request_span:
        request_span.set_attribute("gateway.environment", payload.environment)

        with tracer.start_as_current_span("gateway.auth") as span:
            api_key = _resolve_api_key(db, api_key_value)
            application = _resolve_application(db, api_key)
            set_span_attributes(
                span,
                {
                    "project.id": str(application.project_id),
                    "application.id": str(application.id),
                    "application.slug": application.slug,
                },
            )
            set_span_attributes(
                request_span,
                {
                    "project.id": str(application.project_id),
                    "application.id": str(application.id),
                    "application.slug": application.slug,
                },
            )

        with tracer.start_as_current_span("gateway.prompt_lookup") as span:
            prompt = _resolve_prompt(db, application, payload.prompt_name)
            set_span_attributes(
                span,
                {
                    "prompt.name": prompt.name,
                    "prompt.version": prompt.version,
                    "prompt.id": str(prompt.id),
                },
            )
            set_span_attributes(
                request_span,
                {
                    "prompt.name": prompt.name,
                    "prompt.version": prompt.version,
                },
            )

        with tracer.start_as_current_span("gateway.model_routing") as span:
            route = _resolve_route(db, application, payload.environment)
            route_attributes = {
                "model.provider": route.provider,
                "model.name": route.model_name,
                "model_route.id": str(route.id),
                "model_route.priority": route.priority,
                "model_route.is_default": route.is_default,
            }
            set_span_attributes(span, route_attributes)
            set_span_attributes(request_span, route_attributes)

        settings = get_settings()
        try:
            provider_result = _call_provider_with_retry(
                prompt=prompt,
                route=route,
                user_input=payload.input,
                max_attempts=settings.provider_max_attempts,
                retry_backoff_ms=settings.provider_retry_backoff_ms,
                timeout_seconds=settings.provider_timeout_seconds,
            )
        except MockProviderTimeout as exc:
            gateway_request = _record_failed_request(
                db=db,
                application=application,
                api_key=api_key,
                prompt=prompt,
                route=route,
                latency_ms=_elapsed_ms(started_at),
                error_category="provider_timeout",
            )
            set_span_attributes(
                request_span,
                {
                    "gateway.request_id": gateway_request.request_id,
                    "gateway.status": gateway_request.status,
                    "error.category": gateway_request.error_category,
                },
            )
            record_gateway_request(
                provider=route.provider,
                model=route.model_name,
                environment=payload.environment,
                status=gateway_request.status,
                latency_ms=gateway_request.latency_ms,
                error_category=gateway_request.error_category,
            )
            raise GatewayProviderError(
                "Provider timeout",
                status_code=504,
                error_category="provider_timeout",
            ) from exc
        except MockProviderError as exc:
            gateway_request = _record_failed_request(
                db=db,
                application=application,
                api_key=api_key,
                prompt=prompt,
                route=route,
                latency_ms=_elapsed_ms(started_at),
                error_category="provider_error",
            )
            set_span_attributes(
                request_span,
                {
                    "gateway.request_id": gateway_request.request_id,
                    "gateway.status": gateway_request.status,
                    "error.category": gateway_request.error_category,
                },
            )
            record_gateway_request(
                provider=route.provider,
                model=route.model_name,
                environment=payload.environment,
                status=gateway_request.status,
                latency_ms=gateway_request.latency_ms,
                error_category=gateway_request.error_category,
            )
            raise GatewayProviderError(
                "Provider failure",
                status_code=502,
                error_category="provider_error",
            ) from exc

        latency_ms = _elapsed_ms(started_at)
        estimated_cost = calculate_estimated_cost(
            route.provider,
            route.model_name,
            provider_result.input_tokens,
            provider_result.output_tokens,
        )
        gateway_request = _record_successful_request(
            db=db,
            application=application,
            api_key=api_key,
            prompt=prompt,
            route=route,
            latency_ms=latency_ms,
            input_tokens=provider_result.input_tokens,
            output_tokens=provider_result.output_tokens,
            estimated_cost=estimated_cost,
        )
        set_span_attributes(
            request_span,
            {
                "gateway.request_id": gateway_request.request_id,
                "gateway.status": gateway_request.status,
                "gateway.latency_ms": latency_ms,
                "token.input": provider_result.input_tokens,
                "token.output": provider_result.output_tokens,
                "cost.estimated_usd": float(estimated_cost),
            },
        )
        record_gateway_request(
            provider=route.provider,
            model=route.model_name,
            environment=payload.environment,
            status=gateway_request.status,
            latency_ms=latency_ms,
            input_tokens=provider_result.input_tokens,
            output_tokens=provider_result.output_tokens,
            estimated_cost=estimated_cost,
        )

        with tracer.start_as_current_span("gateway.response_serialization"):
            return CompletionResponse(
                request_id=gateway_request.request_id,
                status=gateway_request.status,
                provider=route.provider,
                model=route.model_name,
                output=provider_result.output,
                prompt_version=prompt.version,
                latency_ms=latency_ms,
                input_tokens=provider_result.input_tokens,
                output_tokens=provider_result.output_tokens,
                estimated_cost_usd=estimated_cost,
            )


def _call_provider_with_retry(
    prompt: PromptVersion,
    route: ModelRoute,
    user_input: str,
    max_attempts: int,
    retry_backoff_ms: int,
    timeout_seconds: int,
) -> MockProviderResult:
    attempts = max(1, max_attempts)
    last_error: MockProviderError | MockProviderTimeout | None = None

    for attempt in range(1, attempts + 1):
        try:
            with tracer.start_as_current_span("gateway.provider_call") as span:
                set_span_attributes(
                    span,
                    {
                        "model.provider": route.provider,
                        "model.name": route.model_name,
                        "provider.attempt": attempt,
                        "provider.max_attempts": attempts,
                        "provider.timeout_seconds": max(1, timeout_seconds),
                    },
                )
                provider_result = complete_with_mock_provider(
                    prompt,
                    route,
                    user_input,
                    attempt=attempt,
                )
                set_span_attributes(
                    span,
                    {
                        "token.input": provider_result.input_tokens,
                        "token.output": provider_result.output_tokens,
                    },
                )
                return provider_result
        except (MockProviderError, MockProviderTimeout) as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            sleep(max(0, retry_backoff_ms) / 1000)

    if last_error is not None:
        raise last_error
    raise MockProviderError("Provider failed without returning a result")


def _record_successful_request(
    db: Session,
    application: Application,
    api_key: ApiKey,
    prompt: PromptVersion,
    route: ModelRoute,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    estimated_cost: Decimal,
) -> GatewayRequest:
    with tracer.start_as_current_span("gateway.database_write") as span:
        gateway_request = GatewayRequest(
            request_id=f"req_{uuid.uuid4().hex}",
            project_id=application.project_id,
            application_id=application.id,
            api_key_id=api_key.id,
            prompt_version_id=prompt.id,
            model_route_id=route.id,
            provider=route.provider,
            model_name=route.model_name,
            status="succeeded",
            latency_ms=latency_ms,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost,
        )
        db.add(gateway_request)
        db.flush()
        db.add(
            CostRecord(
                gateway_request_id=gateway_request.id,
                project_id=application.project_id,
                application_id=application.id,
                provider=route.provider,
                model_name=route.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=estimated_cost,
                currency="USD",
            )
        )
        db.commit()
        set_span_attributes(
            span,
            {
                "gateway.request_id": gateway_request.request_id,
                "gateway.status": gateway_request.status,
            },
        )
        return gateway_request


def _record_failed_request(
    db: Session,
    application: Application,
    api_key: ApiKey,
    prompt: PromptVersion,
    route: ModelRoute,
    latency_ms: int,
    error_category: str,
) -> GatewayRequest:
    with tracer.start_as_current_span("gateway.database_write") as span:
        gateway_request = GatewayRequest(
            request_id=f"req_{uuid.uuid4().hex}",
            project_id=application.project_id,
            application_id=application.id,
            api_key_id=api_key.id,
            prompt_version_id=prompt.id,
            model_route_id=route.id,
            provider=route.provider,
            model_name=route.model_name,
            status="failed",
            latency_ms=latency_ms,
            error_category=error_category,
        )
        db.add(gateway_request)
        db.commit()
        set_span_attributes(
            span,
            {
                "gateway.request_id": gateway_request.request_id,
                "gateway.status": gateway_request.status,
                "error.category": error_category,
            },
        )
        return gateway_request
