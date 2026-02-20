from pydantic import BaseModel
from datetime import datetime


class WebhookRequestResponse(BaseModel):
    id: str
    endpoint_id: str
    method: str
    headers: str
    body: str
    query_params: str
    content_type: str
    source_ip: str
    body_size: int
    created_at: datetime

    model_config = {"from_attributes": True}
