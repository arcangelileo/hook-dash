from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.endpoint import Endpoint

PLAN_ENDPOINT_LIMITS = {
    "free": settings.free_max_endpoints,
    "pro": settings.pro_max_endpoints,
    "team": settings.team_max_endpoints,
}


async def get_endpoint_count(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count(Endpoint.id)).where(Endpoint.user_id == user_id)
    )
    return result.scalar_one()


async def can_create_endpoint(db: AsyncSession, user_id: str, plan: str) -> bool:
    count = await get_endpoint_count(db, user_id)
    limit = PLAN_ENDPOINT_LIMITS.get(plan, settings.free_max_endpoints)
    return count < limit


async def create_endpoint(
    db: AsyncSession,
    user_id: str,
    name: str,
    description: str = "",
    response_code: int = 200,
    response_body: str = '{"ok": true}',
    response_content_type: str = "application/json",
) -> Endpoint:
    endpoint = Endpoint(
        user_id=user_id,
        name=name.strip(),
        description=description.strip(),
        response_code=response_code,
        response_body=response_body,
        response_content_type=response_content_type,
    )
    db.add(endpoint)
    await db.flush()
    return endpoint


async def list_endpoints(db: AsyncSession, user_id: str) -> list[Endpoint]:
    result = await db.execute(
        select(Endpoint)
        .where(Endpoint.user_id == user_id)
        .order_by(Endpoint.created_at.desc())
    )
    return list(result.scalars().all())


async def get_endpoint(db: AsyncSession, endpoint_id: str, user_id: str) -> Endpoint | None:
    result = await db.execute(
        select(Endpoint).where(Endpoint.id == endpoint_id, Endpoint.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_endpoint_by_id(db: AsyncSession, endpoint_id: str) -> Endpoint | None:
    """Get endpoint by ID without user check — used by the webhook receiver."""
    result = await db.execute(select(Endpoint).where(Endpoint.id == endpoint_id))
    return result.scalar_one_or_none()


async def update_endpoint(
    db: AsyncSession,
    endpoint: Endpoint,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
    response_code: int | None = None,
    response_body: str | None = None,
    response_content_type: str | None = None,
) -> Endpoint:
    if name is not None:
        endpoint.name = name.strip()
    if description is not None:
        endpoint.description = description.strip()
    if is_active is not None:
        endpoint.is_active = is_active
    if response_code is not None:
        endpoint.response_code = response_code
    if response_body is not None:
        endpoint.response_body = response_body
    if response_content_type is not None:
        endpoint.response_content_type = response_content_type
    await db.flush()
    return endpoint


async def delete_endpoint(db: AsyncSession, endpoint: Endpoint) -> None:
    await db.delete(endpoint)
    await db.flush()


async def increment_request_count(db: AsyncSession, endpoint: Endpoint) -> None:
    endpoint.request_count = endpoint.request_count + 1
    await db.flush()
