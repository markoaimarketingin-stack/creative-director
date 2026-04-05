from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.api.routes.creatives import router as creatives_router
from app.api.routes.chat import router as chat_router
from app.api.routes.suggestions import router as suggestions_router
from app.core.config import get_settings
from app.services.engine import ServiceContainer
from app.ui import render_homepage

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    container = ServiceContainer(settings)
    app.state.container = container
    yield
    await container.aclose()

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.include_router(creatives_router)
app.include_router(chat_router)
app.include_router(suggestions_router)

@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    return render_homepage(settings)

@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}