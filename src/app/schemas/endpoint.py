from pydantic import BaseModel
from datetime import datetime


class EndpointCreate(BaseModel):
    name: str
    description: str = ""
    response_code: int = 200
    response_body: str = '{"ok": true}'
    response_content_type: str = "application/json"


class EndpointUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    response_code: int | None = None
    response_body: str | None = None
    response_content_type: str | None = None


class EndpointResponse(BaseModel):
    id: str
    name: str
    description: str
    is_active: bool
    response_code: int
    request_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
