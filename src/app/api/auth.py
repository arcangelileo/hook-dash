import re

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_optional_user
from app.models.user import User
from app.services.auth import authenticate_user, create_access_token, register_user

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="src/app/templates")

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _set_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,  # 24 hours
        path="/",
    )


def _validate_registration(email: str, password: str, name: str) -> str | None:
    if not name or len(name.strip()) < 1:
        return "Name is required."
    if not email or not EMAIL_RE.match(email):
        return "Please enter a valid email address."
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    return None


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "auth/register.html")


@router.post("/register")
async def register_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))
    name = str(form.get("name", "")).strip()

    error = _validate_registration(email, password, name)
    if error:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"error": error, "email": email, "name": name},
            status_code=422,
        )

    user = await register_user(db, email, password, name)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"error": "An account with this email already exists.", "email": email, "name": name},
            status_code=409,
        )

    token = create_access_token(user.id)
    response = RedirectResponse(url="/dashboard", status_code=302)
    _set_token_cookie(response, token)
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "auth/login.html")


@router.post("/login")
async def login_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    password = str(form.get("password", ""))

    if not email or not password:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Email and password are required.", "email": email},
            status_code=422,
        )

    user = await authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Invalid email or password.", "email": email},
            status_code=401,
        )

    token = create_access_token(user.id)
    response = RedirectResponse(url="/dashboard", status_code=302)
    _set_token_cookie(response, token)
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token", path="/")
    return response


@router.get("/logout")
async def logout_get():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token", path="/")
    return response
