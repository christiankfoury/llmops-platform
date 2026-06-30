import uuid

from pydantic import BaseModel, ConfigDict, Field


class PromptVersionCreate(BaseModel):
    project_slug: str = Field(min_length=1, max_length=120)
    application_slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    version: int | None = Field(default=None, ge=1)
    is_active: bool = True


class PromptVersionUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    application_id: uuid.UUID | None
    name: str
    version: int
    content: str
    is_active: bool


class ModelRouteCreate(BaseModel):
    project_slug: str = Field(min_length=1, max_length=120)
    application_slug: str = Field(min_length=1, max_length=120)
    environment: str = Field(default="local", min_length=1, max_length=40)
    provider: str = Field(default="mock", min_length=1, max_length=80)
    model_name: str = Field(min_length=1, max_length=160)
    priority: int = Field(default=100, ge=1)
    is_default: bool = True
    is_active: bool = True


class ModelRouteUpdate(BaseModel):
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    model_name: str | None = Field(default=None, min_length=1, max_length=160)
    priority: int | None = Field(default=None, ge=1)
    is_default: bool | None = None
    is_active: bool | None = None


class ModelRouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    application_id: uuid.UUID | None
    environment: str
    provider: str
    model_name: str
    priority: int
    is_default: bool
    is_active: bool
