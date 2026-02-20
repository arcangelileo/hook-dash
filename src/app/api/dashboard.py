from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="src/app/templates")

PLAN_ENDPOINT_LIMITS = {
    "free": settings.free_max_endpoints,
    "pro": settings.pro_max_endpoints,
    "team": settings.team_max_endpoints,
}


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user)):
    plan_limit = PLAN_ENDPOINT_LIMITS.get(user.plan, settings.free_max_endpoints)
    return templates.TemplateResponse(
        request, "dashboard/index.html", {"user": user, "plan_limit": plan_limit}
    )
