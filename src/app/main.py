from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.endpoints import router as endpoints_router
from app.api.receiver import router as receiver_router
from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Webhook inspection, debugging, and forwarding platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(endpoints_router)
app.include_router(receiver_router)

templates = Jinja2Templates(directory="src/app/templates")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/auth/login", status_code=302)
    return HTMLResponse(
        content=f"Error {exc.status_code}: {exc.detail}", status_code=exc.status_code
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name, "version": "0.1.0"}


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(request, "landing.html")
