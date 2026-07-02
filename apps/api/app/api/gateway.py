"""HTTP entrypoints for the LLM gateway.

This module keeps request/response concerns at the API boundary: headers,
rate-limit rejection, and conversion of service exceptions into HTTP errors.
The gateway service owns the actual project/app, prompt, routing, provider,
and persistence workflow.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.observability.metrics import (
    record_gateway_auth_failure,
    record_gateway_config_error,
    record_gateway_rate_limit_rejection,
)
from app.schemas.gateway import CompletionRequest, CompletionResponse
from app.services.auth import hash_api_key
from app.services.gateway import (
    GatewayAuthError,
    GatewayConfigError,
    GatewayProviderError,
    process_completion,
)
from app.services.rate_limit import check_rate_limit

router = APIRouter(prefix="/v1/gateway", tags=["gateway"])


@router.post("/completions", response_model=CompletionResponse)
def create_completion(
    payload: CompletionRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> CompletionResponse:
    """Handle a completion request from a client application.

    The client authenticates with `X-API-Key`. The key is rate-limited before
    the deeper gateway flow runs so obviously excessive traffic is rejected
    before database lookups and provider work.
    """
    if not x_api_key:
        record_gateway_auth_failure(payload.environment)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    settings = get_settings()
    if settings.rate_limit_enabled and not check_rate_limit(
        identifier=hash_api_key(x_api_key),
        limit=settings.rate_limit_requests_per_minute,
        window_seconds=settings.rate_limit_window_seconds,
    ):
        record_gateway_rate_limit_rejection()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    try:
        return process_completion(db=db, api_key_value=x_api_key, payload=payload)
    except GatewayAuthError as exc:
        record_gateway_auth_failure(payload.environment)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except GatewayConfigError as exc:
        record_gateway_config_error(payload.environment)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GatewayProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
