from pydantic import BaseModel, Field


class CompletionRequest(BaseModel):
    input: str = Field(min_length=1, max_length=8000)
    prompt_name: str = Field(default="default-chat", min_length=1, max_length=160)
    environment: str = Field(default="local", min_length=1, max_length=40)


class CompletionResponse(BaseModel):
    request_id: str
    status: str
    provider: str
    model: str
    output: str
    prompt_version: int
