from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.endpoint import get_endpoint_count, list_endpoints, PLAN_ENDPOINT_LIMITS
from app.services.receiver import get_requests_today_count, get_total_requests_count

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="src/app/templates")


@router.get("", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    endpoint_count = await get_endpoint_count(db, user.id)
    requests_today = await get_requests_today_count(db, user.id)
    total_requests = await get_total_requests_count(db, user.id)
    plan_limit = PLAN_ENDPOINT_LIMITS.get(user.plan, settings.free_max_endpoints)
    recent_endpoints = await list_endpoints(db, user.id)

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "user": user,
            "endpoint_count": endpoint_count,
            "requests_today": requests_today,
            "total_requests": total_requests,
            "plan_limit": plan_limit,
            "endpoints": recent_endpoints[:5],
        },
    )
