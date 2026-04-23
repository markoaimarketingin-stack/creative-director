from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.routes.creatives import router as creatives_router
from app.api.routes.chat import router as chat_router
from app.api.routes.suggestions import router as suggestions_router
from app.core.config import get_settings
from app.services.engine import ServiceContainer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

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
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/ui-config")
async def ui_config() -> dict[str, str]:
    return {
        "app_name": settings.app_name,
        "groq_status": "Connected" if settings.groq_api_key else "Missing key",
        "nanobanana_status": "Configured" if settings.nanobanana_api_key else "Unavailable",
    }

@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}