from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.endpoint import (
    can_create_endpoint,
    create_endpoint,
    delete_endpoint,
    get_endpoint,
    list_endpoints,
    update_endpoint,
    PLAN_ENDPOINT_LIMITS,
)
from app.services.forwarding import get_forwarding_config, get_forwarding_stats
from app.services.receiver import list_webhook_requests

router = APIRouter(prefix="/endpoints", tags=["endpoints"])
templates = Jinja2Templates(directory="src/app/templates")


@router.get("", response_class=HTMLResponse)
async def endpoints_list(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    endpoints = await list_endpoints(db, user.id)
    plan_limit = PLAN_ENDPOINT_LIMITS.get(user.plan, settings.free_max_endpoints)
    return templates.TemplateResponse(
        request,
        "endpoints/list.html",
        {
            "user": user,
            "endpoints": endpoints,
            "plan_limit": plan_limit,
            "endpoint_count": len(endpoints),
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def endpoint_new_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    can_create = await can_create_endpoint(db, user.id, user.plan)
    if not can_create:
        plan_limit = PLAN_ENDPOINT_LIMITS.get(user.plan, settings.free_max_endpoints)
        return templates.TemplateResponse(
            request,
            "endpoints/new.html",
            {
                "user": user,
                "error": f"You've reached your plan limit of {plan_limit} endpoints. Upgrade to create more.",
                "at_limit": True,
            },
        )
    return templates.TemplateResponse(request, "endpoints/new.html", {"user": user})


@router.post("/new")
async def endpoint_create(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    name = str(form.get("name", "")).strip()
    description = str(form.get("description", "")).strip()
    response_code = int(form.get("response_code", 200))
    response_body = str(form.get("response_body", '{"ok": true}'))
    response_content_type = str(form.get("response_content_type", "application/json"))

    if not name:
        return templates.TemplateResponse(
            request,
            "endpoints/new.html",
            {"user": user, "error": "Endpoint name is required.", "form": form},
            status_code=422,
        )

    if len(name) > 255:
        return templates.TemplateResponse(
            request,
            "endpoints/new.html",
            {"user": user, "error": "Name must be under 255 characters.", "form": form},
            status_code=422,
        )

    if response_code < 100 or response_code > 599:
        return templates.TemplateResponse(
            request,
            "endpoints/new.html",
            {"user": user, "error": "Response code must be between 100 and 599.", "form": form},
            status_code=422,
        )

    can_create = await can_create_endpoint(db, user.id, user.plan)
    if not can_create:
        return templates.TemplateResponse(
            request,
            "endpoints/new.html",
            {"user": user, "error": "You've reached your endpoint limit. Upgrade your plan."},
            status_code=403,
        )

    endpoint = await create_endpoint(
        db, user.id, name, description, response_code, response_body, response_content_type
    )
    return RedirectResponse(url=f"/endpoints/{endpoint.id}", status_code=302)


@router.get("/{endpoint_id}", response_class=HTMLResponse)
async def endpoint_detail(
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

    method_filter = request.query_params.get("method")
    search = request.query_params.get("search")
    page = int(request.query_params.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    requests_list, total = await list_webhook_requests(
        db, endpoint_id, limit=per_page, offset=offset,
        method_filter=method_filter, search=search,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)
    webhook_url = f"{request.base_url}hooks/{endpoint.id}"

    # Get forwarding config and stats
    fwd_config = await get_forwarding_config(db, endpoint_id)
    fwd_stats = None
    if fwd_config:
        fwd_stats = await get_forwarding_stats(db, fwd_config.id)

    fwd_error = request.query_params.get("fwd_error")

    return templates.TemplateResponse(
        request,
        "endpoints/detail.html",
        {
            "user": user,
            "endpoint": endpoint,
            "webhook_requests": requests_list,
            "webhook_url": webhook_url,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "method_filter": method_filter or "",
            "search": search or "",
            "fwd_config": fwd_config,
            "fwd_stats": fwd_stats,
            "fwd_error": fwd_error,
        },
    )


@router.get("/{endpoint_id}/edit", response_class=HTMLResponse)
async def endpoint_edit_page(
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
    return templates.TemplateResponse(
        request, "endpoints/edit.html", {"user": user, "endpoint": endpoint}
    )


@router.post("/{endpoint_id}/edit")
async def endpoint_update(
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

    form = await request.form()
    name = str(form.get("name", "")).strip()
    description = str(form.get("description", "")).strip()
    is_active = form.get("is_active") == "on"
    response_code = int(form.get("response_code", endpoint.response_code))
    response_body = str(form.get("response_body", endpoint.response_body))
    response_content_type = str(form.get("response_content_type", endpoint.response_content_type))

    if not name:
        return templates.TemplateResponse(
            request,
            "endpoints/edit.html",
            {"user": user, "endpoint": endpoint, "error": "Endpoint name is required."},
            status_code=422,
        )

    if response_code < 100 or response_code > 599:
        return templates.TemplateResponse(
            request,
            "endpoints/edit.html",
            {"user": user, "endpoint": endpoint, "error": "Response code must be between 100 and 599."},
            status_code=422,
        )

    await update_endpoint(
        db, endpoint, name, description, is_active, response_code, response_body, response_content_type
    )
    return RedirectResponse(url=f"/endpoints/{endpoint_id}", status_code=302)


@router.post("/{endpoint_id}/delete")
async def endpoint_remove(
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
    await delete_endpoint(db, endpoint)
    return RedirectResponse(url="/endpoints", status_code=302)
