import json
import time
import logging
import asyncio

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forwarding import ForwardingConfig, ForwardingLog
from app.models.webhook_request import WebhookRequest

logger = logging.getLogger(__name__)


async def get_forwarding_config(db: AsyncSession, endpoint_id: str) -> ForwardingConfig | None:
    result = await db.execute(
        select(ForwardingConfig).where(ForwardingConfig.endpoint_id == endpoint_id)
    )
    return result.scalar_one_or_none()


async def create_forwarding_config(
    db: AsyncSession,
    endpoint_id: str,
    target_url: str,
    is_active: bool = True,
    max_retries: int = 5,
    timeout_seconds: int = 30,
) -> ForwardingConfig:
    config = ForwardingConfig(
        endpoint_id=endpoint_id,
        target_url=target_url.strip(),
        is_active=is_active,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
    db.add(config)
    await db.flush()
    return config


async def update_forwarding_config(
    db: AsyncSession,
    config: ForwardingConfig,
    target_url: str | None = None,
    is_active: bool | None = None,
    max_retries: int | None = None,
    timeout_seconds: int | None = None,
) -> ForwardingConfig:
    if target_url is not None:
        config.target_url = target_url.strip()
    if is_active is not None:
        config.is_active = is_active
    if max_retries is not None:
        config.max_retries = max_retries
    if timeout_seconds is not None:
        config.timeout_seconds = timeout_seconds
    await db.flush()
    return config


async def delete_forwarding_config(db: AsyncSession, config: ForwardingConfig) -> None:
    await db.delete(config)
    await db.flush()


async def create_forwarding_log(
    db: AsyncSession,
    forwarding_config_id: str,
    webhook_request_id: str,
    status_code: int | None,
    success: bool,
    error_message: str = "",
    attempt_number: int = 1,
    response_time_ms: int | None = None,
) -> ForwardingLog:
    log = ForwardingLog(
        forwarding_config_id=forwarding_config_id,
        webhook_request_id=webhook_request_id,
        status_code=status_code,
        success=success,
        error_message=error_message,
        attempt_number=attempt_number,
        response_time_ms=response_time_ms,
    )
    db.add(log)
    await db.flush()
    return log


async def list_forwarding_logs(
    db: AsyncSession,
    forwarding_config_id: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ForwardingLog], int]:
    count_query = select(func.count(ForwardingLog.id)).where(
        ForwardingLog.forwarding_config_id == forwarding_config_id
    )
    total = (await db.execute(count_query)).scalar_one()

    result = await db.execute(
        select(ForwardingLog)
        .where(ForwardingLog.forwarding_config_id == forwarding_config_id)
        .order_by(ForwardingLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def get_forwarding_stats(
    db: AsyncSession, forwarding_config_id: str
) -> dict:
    """Return summary stats for a forwarding config."""
    total_result = await db.execute(
        select(func.count(ForwardingLog.id)).where(
            ForwardingLog.forwarding_config_id == forwarding_config_id
        )
    )
    total = total_result.scalar_one()

    success_result = await db.execute(
        select(func.count(ForwardingLog.id)).where(
            ForwardingLog.forwarding_config_id == forwarding_config_id,
            ForwardingLog.success.is_(True),
        )
    )
    successes = success_result.scalar_one()

    failed = total - successes

    avg_result = await db.execute(
        select(func.avg(ForwardingLog.response_time_ms)).where(
            ForwardingLog.forwarding_config_id == forwarding_config_id,
            ForwardingLog.response_time_ms.isnot(None),
        )
    )
    avg_time = avg_result.scalar_one()

    return {
        "total": total,
        "successes": successes,
        "failures": failed,
        "success_rate": round((successes / total * 100) if total > 0 else 0, 1),
        "avg_response_ms": int(avg_time) if avg_time else 0,
    }


async def forward_webhook(
    db: AsyncSession,
    config: ForwardingConfig,
    webhook_request: WebhookRequest,
    attempt: int = 1,
) -> ForwardingLog:
    """Forward a single webhook request to the target URL and log the result."""
    headers = {}
    try:
        original_headers = json.loads(webhook_request.headers)
        skip_headers = {"host", "content-length", "transfer-encoding", "connection"}
        for k, v in original_headers.items():
            if k.lower() not in skip_headers:
                headers[k] = v
    except (json.JSONDecodeError, TypeError):
        pass

    headers["X-HookDash-Request-Id"] = webhook_request.id
    headers["X-HookDash-Attempt"] = str(attempt)

    status_code = None
    success = False
    error_message = ""
    response_time_ms = None

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as http_client:
            resp = await http_client.request(
                method=webhook_request.method,
                url=config.target_url,
                content=webhook_request.body.encode("utf-8") if webhook_request.body else b"",
                headers=headers,
            )
            status_code = resp.status_code
            success = 200 <= resp.status_code < 300
            if not success:
                error_message = f"HTTP {resp.status_code}"
    except httpx.TimeoutException:
        error_message = f"Timeout after {config.timeout_seconds}s"
    except httpx.ConnectError:
        error_message = "Connection refused"
    except Exception as e:
        error_message = str(e)[:500]

    elapsed = time.monotonic() - start
    response_time_ms = int(elapsed * 1000)

    log = await create_forwarding_log(
        db=db,
        forwarding_config_id=config.id,
        webhook_request_id=webhook_request.id,
        status_code=status_code,
        success=success,
        error_message=error_message,
        attempt_number=attempt,
        response_time_ms=response_time_ms,
    )
    return log


async def forward_with_retries(
    db: AsyncSession,
    config: ForwardingConfig,
    webhook_request: WebhookRequest,
) -> ForwardingLog:
    """Forward with exponential backoff retries. Returns the final log entry."""
    log = None
    for attempt in range(1, config.max_retries + 1):
        log = await forward_webhook(db, config, webhook_request, attempt)
        if log.success:
            return log
        if attempt < config.max_retries:
            delay = min(2 ** (attempt - 1), 30)
            await asyncio.sleep(delay)
    return log
