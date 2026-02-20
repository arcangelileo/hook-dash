from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.endpoint import get_endpoint_by_id
from app.services.receiver import store_webhook_request

router = APIRouter(tags=["receiver"])


@router.api_route(
    "/hooks/{endpoint_id}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def receive_webhook(
    endpoint_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    endpoint = await get_endpoint_by_id(db, endpoint_id)
    if not endpoint:
        return Response(
            content='{"error": "Endpoint not found"}',
            status_code=404,
            media_type="application/json",
        )

    if not endpoint.is_active:
        return Response(
            content='{"error": "Endpoint is inactive"}',
            status_code=410,
            media_type="application/json",
        )

    body_bytes = await request.body()
    if len(body_bytes) > settings.max_body_size:
        return Response(
            content='{"error": "Request body too large (max 1MB)"}',
            status_code=413,
            media_type="application/json",
        )

    body = body_bytes.decode("utf-8", errors="replace")
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    content_type = request.headers.get("content-type", "")
    source_ip = request.client.host if request.client else "unknown"

    await store_webhook_request(
        db=db,
        endpoint=endpoint,
        method=request.method,
        headers=headers,
        body=body,
        query_params=query_params,
        content_type=content_type,
        source_ip=source_ip,
    )

    return Response(
        content=endpoint.response_body,
        status_code=endpoint.response_code,
        media_type=endpoint.response_content_type,
    )
