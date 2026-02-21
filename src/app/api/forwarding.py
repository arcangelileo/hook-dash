from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.endpoint import get_endpoint
from app.services.forwarding import (
    create_forwarding_config,
    delete_forwarding_config,
    forward_webhook,
    get_forwarding_config,
    list_forwarding_logs,
    update_forwarding_config,
)
from app.services.receiver import get_webhook_request

router = APIRouter(tags=["forwarding"])
templates = Jinja2Templates(directory="src/app/templates")


@router.post("/endpoints/{endpoint_id}/forwarding")
async def save_forwarding(
    endpoint_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    endpoint = await get_endpoint(db, endpoint_id, user.id)
    if not endpoint:
        return RedirectResponse(url="/endpoints", status_code=302)

    form = await request.form()
    target_url = str(form.get("target_url", "")).strip()
    is_active = form.get("is_active") == "on"
    try:
        max_retries = int(form.get("max_retries", 5))
    except (ValueError, TypeError):
        max_retries = 5
    try:
        timeout_seconds = int(form.get("timeout_seconds", 30))
    except (ValueError, TypeError):
        timeout_seconds = 30

    if not target_url:
        return RedirectResponse(
            url=f"/endpoints/{endpoint_id}?fwd_error=Target+URL+is+required",
            status_code=302,
        )

    if not target_url.startswith(("http://", "https://")):
        return RedirectResponse(
            url=f"/endpoints/{endpoint_id}?fwd_error=URL+must+start+with+http://+or+https://",
            status_code=302,
        )

    max_retries = max(1, min(max_retries, 10))
    timeout_seconds = max(5, min(timeout_seconds, 120))

    config = await get_forwarding_config(db, endpoint_id)
    if config:
        await update_forwarding_config(
            db, config, target_url, is_active, max_retries, timeout_seconds
        )
    else:
        await create_forwarding_config(
            db, endpoint_id, target_url, is_active, max_retries, timeout_seconds
        )

    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=302)


@router.post("/endpoints/{endpoint_id}/forwarding/delete")
async def remove_forwarding(
    endpoint_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    endpoint = await get_endpoint(db, endpoint_id, user.id)
    if not endpoint:
        return RedirectResponse(url="/endpoints", status_code=302)

    config = await get_forwarding_config(db, endpoint_id)
    if config:
        await delete_forwarding_config(db, config)

    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=302)


@router.get("/endpoints/{endpoint_id}/forwarding/logs", response_class=HTMLResponse)
async def forwarding_logs_page(
    endpoint_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    endpoint = await get_endpoint(db, endpoint_id, user.id)
    if not endpoint:
        return templates.TemplateResponse(
            request, "endpoints/not_found.html", {"user": user}, status_code=404
        )

    config = await get_forwarding_config(db, endpoint_id)
    if not config:
        return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=302)

    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    per_page = 50
    offset = (page - 1) * per_page

    logs, total = await list_forwarding_logs(db, config.id, limit=per_page, offset=offset)
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse(
        request,
        "forwarding/logs.html",
        {
            "user": user,
            "endpoint": endpoint,
            "config": config,
            "logs": logs,
            "total": total,
            "page": page,
            "total_pages": total_pages,
        },
    )


@router.post("/endpoints/{endpoint_id}/replay/{request_id}")
async def replay_webhook(
    endpoint_id: str,
    request_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    endpoint = await get_endpoint(db, endpoint_id, user.id)
    if not endpoint:
        return RedirectResponse(url="/endpoints", status_code=302)

    config = await get_forwarding_config(db, endpoint_id)
    if not config or not config.is_active:
        return RedirectResponse(
            url=f"/endpoints/{endpoint_id}?fwd_error=Forwarding+not+configured+or+inactive",
            status_code=302,
        )

    webhook_req = await get_webhook_request(db, request_id, endpoint_id)
    if not webhook_req:
        return RedirectResponse(
            url=f"/endpoints/{endpoint_id}?fwd_error=Request+not+found",
            status_code=302,
        )

    await forward_webhook(db, config, webhook_req)
    return RedirectResponse(
        url=f"/endpoints/{endpoint_id}/forwarding/logs", status_code=302
    )
