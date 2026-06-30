import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.admin import (
    ModelRouteCreate,
    ModelRouteResponse,
    ModelRouteUpdate,
    PromptVersionCreate,
    PromptVersionResponse,
    PromptVersionUpdate,
)
from app.services.admin_config import (
    AdminConfigError,
    activate_model_route,
    activate_prompt_version,
    create_model_route,
    create_prompt_version,
    list_model_routes,
    list_prompt_versions,
    update_model_route,
    update_prompt_version,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def _actor_id(value: str | None) -> str:
    return value or "local-admin"


@router.get("/prompt-versions", response_model=list[PromptVersionResponse])
def read_prompt_versions(db: Session = Depends(get_db)) -> list[PromptVersionResponse]:
    return list_model_prompt_responses(list_prompt_versions(db))


@router.post(
    "/prompt-versions",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_prompt(
    payload: PromptVersionCreate,
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
) -> PromptVersionResponse:
    try:
        prompt = create_prompt_version(db, payload, actor_id=_actor_id(x_actor_id))
    except AdminConfigError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PromptVersionResponse.model_validate(prompt)


@router.patch("/prompt-versions/{prompt_id}", response_model=PromptVersionResponse)
def update_prompt(
    prompt_id: uuid.UUID,
    payload: PromptVersionUpdate,
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
) -> PromptVersionResponse:
    try:
        prompt = update_prompt_version(db, prompt_id, payload, actor_id=_actor_id(x_actor_id))
    except AdminConfigError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PromptVersionResponse.model_validate(prompt)


@router.post("/prompt-versions/{prompt_id}/activate", response_model=PromptVersionResponse)
def activate_prompt(
    prompt_id: uuid.UUID,
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
) -> PromptVersionResponse:
    try:
        prompt = activate_prompt_version(db, prompt_id, actor_id=_actor_id(x_actor_id))
    except AdminConfigError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PromptVersionResponse.model_validate(prompt)


@router.get("/model-routes", response_model=list[ModelRouteResponse])
def read_model_routes(db: Session = Depends(get_db)) -> list[ModelRouteResponse]:
    return [ModelRouteResponse.model_validate(route) for route in list_model_routes(db)]


@router.post(
    "/model-routes",
    response_model=ModelRouteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_route(
    payload: ModelRouteCreate,
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
) -> ModelRouteResponse:
    try:
        route = create_model_route(db, payload, actor_id=_actor_id(x_actor_id))
    except AdminConfigError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ModelRouteResponse.model_validate(route)


@router.patch("/model-routes/{route_id}", response_model=ModelRouteResponse)
def update_route(
    route_id: uuid.UUID,
    payload: ModelRouteUpdate,
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
) -> ModelRouteResponse:
    try:
        route = update_model_route(db, route_id, payload, actor_id=_actor_id(x_actor_id))
    except AdminConfigError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ModelRouteResponse.model_validate(route)


@router.post("/model-routes/{route_id}/activate", response_model=ModelRouteResponse)
def activate_route(
    route_id: uuid.UUID,
    x_actor_id: str | None = Header(default=None, alias="X-Actor-ID"),
    db: Session = Depends(get_db),
) -> ModelRouteResponse:
    try:
        route = activate_model_route(db, route_id, actor_id=_actor_id(x_actor_id))
    except AdminConfigError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ModelRouteResponse.model_validate(route)


def list_model_prompt_responses(prompts) -> list[PromptVersionResponse]:
    return [PromptVersionResponse.model_validate(prompt) for prompt in prompts]
