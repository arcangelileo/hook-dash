import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, async_session
from app.services.endpoint import get_endpoint_by_id
from app.services.forwarding import forward_with_retries, get_forwarding_config
from app.services.receiver import store_webhook_request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["receiver"])


async def _forward_in_background(
    forwarding_config_id: str,
    forwarding_config_target_url: str,
    forwarding_config_max_retries: int,
    forwarding_config_timeout_seconds: int,
    webhook_request_id: str,
    endpoint_id: str,
):
    """Background task to forward a webhook request with retries.

    Uses its own database session since background tasks run outside
    the request lifecycle.
    """
    from app.models.forwarding import ForwardingConfig
    from app.models.webhook_request import WebhookRequest
    from sqlalchemy import select

    async with async_session() as db:
        try:
            # Re-fetch objects in this session
            config_result = await db.execute(
                select(ForwardingConfig).where(ForwardingConfig.id == forwarding_config_id)
            )
            config = config_result.scalar_one_or_none()

            req_result = await db.execute(
                select(WebhookRequest).where(WebhookRequest.id == webhook_request_id)
            )
            webhook_req = req_result.scalar_one_or_none()

            if config and webhook_req and config.is_active:
                await forward_with_retries(db, config, webhook_req)
                await db.commit()
        except Exception:
            logger.exception(
                "Background forwarding failed for request %s -> %s",
                webhook_request_id,
                forwarding_config_target_url,
            )
            await db.rollback()


@router.api_route(
    "/hooks/{endpoint_id}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def receive_webhook(
    endpoint_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
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

    # Pre-check Content-Length header to reject obviously too-large requests early
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > settings.max_body_size:
        return Response(
            content='{"error": "Request body too large (max 1MB)"}',
            status_code=413,
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

    webhook_req = await store_webhook_request(
        db=db,
        endpoint=endpoint,
        method=request.method,
        headers=headers,
        body=body,
        query_params=query_params,
        content_type=content_type,
        source_ip=source_ip,
    )

    # Auto-forward if forwarding is configured and active
    fwd_config = await get_forwarding_config(db, endpoint_id)
    if fwd_config and fwd_config.is_active:
        background_tasks.add_task(
            _forward_in_background,
            forwarding_config_id=fwd_config.id,
            forwarding_config_target_url=fwd_config.target_url,
            forwarding_config_max_retries=fwd_config.max_retries,
            forwarding_config_timeout_seconds=fwd_config.timeout_seconds,
            webhook_request_id=webhook_req.id,
            endpoint_id=endpoint_id,
        )

    return Response(
        content=endpoint.response_body,
        status_code=endpoint.response_code,
        media_type=endpoint.response_content_type,
    )
