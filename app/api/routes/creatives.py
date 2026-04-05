from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.models import CampaignPackage, CreativeInput, Platform, TopCreativesResponse
from app.services.engine import CreativeDirectorEngine, ServiceContainer

router = APIRouter(tags=["creatives"])


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


def get_engine(container: ServiceContainer = Depends(get_container)) -> CreativeDirectorEngine:
    return container.engine


@router.post("/generate-creatives", response_model=CampaignPackage)
async def generate_creatives(
    payload: CreativeInput,
    engine: CreativeDirectorEngine = Depends(get_engine),
) -> CampaignPackage:
    try:
        return await engine.generate_campaign(payload)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/top-creatives", response_model=TopCreativesResponse)
async def get_top_creatives(
    limit: int = Query(default=10, ge=1, le=50),
    platform: Platform | None = None,
    engine: CreativeDirectorEngine = Depends(get_engine),
) -> TopCreativesResponse:
    return engine.get_top_creatives(limit=limit, platform=platform)
