from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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

templates = Jinja2Templates(directory="src/app/templates")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name, "version": "0.1.0"}


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(request, "landing.html")
