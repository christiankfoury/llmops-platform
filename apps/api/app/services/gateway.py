import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey, Application, GatewayRequest, ModelRoute, PromptVersion
from app.schemas.gateway import CompletionRequest, CompletionResponse
from app.services.auth import hash_api_key
from app.services.mock_provider import complete_with_mock_provider


class GatewayAuthError(Exception):
    pass


class GatewayConfigError(Exception):
    pass


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
    api_key = _resolve_api_key(db, api_key_value)
    application = _resolve_application(db, api_key)
    prompt = _resolve_prompt(db, application, payload.prompt_name)
    route = _resolve_route(db, application, payload.environment)
    provider_result = complete_with_mock_provider(prompt, route, payload.input)

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
    )
    db.add(gateway_request)
    db.commit()

    return CompletionResponse(
        request_id=gateway_request.request_id,
        status=gateway_request.status,
        provider=route.provider,
        model=route.model_name,
        output=provider_result.output,
        prompt_version=prompt.version,
    )
