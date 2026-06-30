import uuid
from decimal import Decimal
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey, Application, CostRecord, GatewayRequest, ModelRoute, PromptVersion
from app.schemas.gateway import CompletionRequest, CompletionResponse
from app.services.auth import hash_api_key
from app.services.mock_provider import (
    MockProviderError,
    MockProviderTimeout,
    complete_with_mock_provider,
)
from app.services.pricing import calculate_estimated_cost


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
    api_key = _resolve_api_key(db, api_key_value)
    application = _resolve_application(db, api_key)
    prompt = _resolve_prompt(db, application, payload.prompt_name)
    route = _resolve_route(db, application, payload.environment)

    try:
        provider_result = complete_with_mock_provider(prompt, route, payload.input)
    except MockProviderTimeout as exc:
        _record_failed_request(
            db=db,
            application=application,
            api_key=api_key,
            prompt=prompt,
            route=route,
            latency_ms=_elapsed_ms(started_at),
            error_category="provider_timeout",
        )
        raise GatewayProviderError(
            "Provider timeout",
            status_code=504,
            error_category="provider_timeout",
        ) from exc
    except MockProviderError as exc:
        _record_failed_request(
            db=db,
            application=application,
            api_key=api_key,
            prompt=prompt,
            route=route,
            latency_ms=_elapsed_ms(started_at),
            error_category="provider_error",
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
    return gateway_request
