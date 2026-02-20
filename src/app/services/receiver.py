import json

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_request import WebhookRequest
from app.models.endpoint import Endpoint
from app.services.endpoint import increment_request_count


async def store_webhook_request(
    db: AsyncSession,
    endpoint: Endpoint,
    method: str,
    headers: dict,
    body: str,
    query_params: dict,
    content_type: str,
    source_ip: str,
) -> WebhookRequest:
    webhook_req = WebhookRequest(
        endpoint_id=endpoint.id,
        method=method.upper(),
        headers=json.dumps(dict(headers)),
        body=body,
        query_params=json.dumps(dict(query_params)),
        content_type=content_type,
        source_ip=source_ip,
        body_size=len(body.encode("utf-8")) if body else 0,
    )
    db.add(webhook_req)
    await increment_request_count(db, endpoint)
    await db.flush()
    return webhook_req


async def list_webhook_requests(
    db: AsyncSession,
    endpoint_id: str,
    limit: int = 50,
    offset: int = 0,
    method_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[WebhookRequest], int]:
    """Return (requests, total_count) for an endpoint with optional filters."""
    query = select(WebhookRequest).where(WebhookRequest.endpoint_id == endpoint_id)
    count_query = select(func.count(WebhookRequest.id)).where(
        WebhookRequest.endpoint_id == endpoint_id
    )

    if method_filter:
        query = query.where(WebhookRequest.method == method_filter.upper())
        count_query = count_query.where(WebhookRequest.method == method_filter.upper())

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            WebhookRequest.body.like(search_pattern)
            | WebhookRequest.headers.like(search_pattern)
            | WebhookRequest.query_params.like(search_pattern)
        )
        count_query = count_query.where(
            WebhookRequest.body.like(search_pattern)
            | WebhookRequest.headers.like(search_pattern)
            | WebhookRequest.query_params.like(search_pattern)
        )

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(WebhookRequest.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total


async def get_webhook_request(
    db: AsyncSession, request_id: str, endpoint_id: str
) -> WebhookRequest | None:
    result = await db.execute(
        select(WebhookRequest).where(
            WebhookRequest.id == request_id,
            WebhookRequest.endpoint_id == endpoint_id,
        )
    )
    return result.scalar_one_or_none()


async def get_requests_today_count(db: AsyncSession, user_id: str) -> int:
    """Count all webhook requests received today for all of a user's endpoints."""
    result = await db.execute(
        select(func.count(WebhookRequest.id))
        .join(Endpoint, WebhookRequest.endpoint_id == Endpoint.id)
        .where(
            Endpoint.user_id == user_id,
            func.date(WebhookRequest.created_at) == func.date(func.now()),
        )
    )
    return result.scalar_one()


async def get_total_requests_count(db: AsyncSession, user_id: str) -> int:
    """Count all webhook requests ever received for a user's endpoints."""
    result = await db.execute(
        select(func.count(WebhookRequest.id))
        .join(Endpoint, WebhookRequest.endpoint_id == Endpoint.id)
        .where(Endpoint.user_id == user_id)
    )
    return result.scalar_one()
