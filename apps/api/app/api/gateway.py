from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.gateway import CompletionRequest, CompletionResponse
from app.services.gateway import GatewayAuthError, GatewayConfigError, process_completion

router = APIRouter(prefix="/v1/gateway", tags=["gateway"])


@router.post("/completions", response_model=CompletionResponse)
def create_completion(
    payload: CompletionRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> CompletionResponse:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    try:
        return process_completion(db=db, api_key_value=x_api_key, payload=payload)
    except GatewayAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except GatewayConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
