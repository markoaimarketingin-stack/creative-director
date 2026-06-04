from fastapi import APIRouter, Depends
import httpx

from app.core.config import get_settings
from app.auth import get_current_user

router = APIRouter(tags=["providers"])


@router.get("/provider-health")
async def provider_health(current_user: dict = Depends(get_current_user)) -> dict:
    settings = get_settings()
    health: dict[str, dict[str, str | bool]] = {
        "groq": {"configured": bool(settings.groq_api_key), "ok": False, "detail": "Not checked"},
        "gemini": {"configured": bool(settings.gemini_api_key), "ok": False, "detail": "Not checked"},
        "huggingface": {"configured": bool(settings.hf_api_key), "ok": False, "detail": "Not checked"},
    }

    if settings.groq_api_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": settings.groq_model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    }
                )
                response.raise_for_status()
            health["groq"]["ok"] = True
            health["groq"]["detail"] = "Reachable"
        except Exception as exc:
            health["groq"]["detail"] = str(exc)
    else:
        health["groq"]["detail"] = "Missing GROQ_API_KEY"

    if settings.gemini_api_key:
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(
                    f"{settings.gemini_base_url.rstrip('/')}/{settings.gemini_model}:generateContent",
                    headers={"Content-Type": "application/json"},
                    params={"key": settings.gemini_api_key},
                    json={
                        "contents": [{"parts": [{"text": "Return JSON: {\"ok\": true}"}]}],
                        "generationConfig": {"response_mime_type": "application/json", "temperature": 0},
                    },
                )
                response.raise_for_status()
            health["gemini"]["ok"] = True
            health["gemini"]["detail"] = "Reachable"
        except Exception as exc:
            health["gemini"]["detail"] = str(exc)
    else:
        health["gemini"]["detail"] = "Missing GEMINI_API_KEY"

    if settings.hf_api_key:
        model = settings.hf_image_model.strip()
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.post(
                    f"https://router.huggingface.co/hf-inference/models/{model}",
                    headers={
                        "Authorization": f"Bearer {settings.hf_api_key.strip()}",
                        "Accept": "*/*",
                        "Content-Type": "application/json",
                    },
                    json={"inputs": "A studio product photo of a luxury watch, clean background"},
                )
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "image" not in content_type:
                    raise RuntimeError(f"Non-image response: {content_type}")
            health["huggingface"]["ok"] = True
            health["huggingface"]["detail"] = f"Reachable ({model})"
        except Exception as exc:
            health["huggingface"]["detail"] = str(exc)
    else:
        health["huggingface"]["detail"] = "Missing HF_API_KEY"

    return health


from pydantic import BaseModel
from app.services.database import ChatDatabase


class SaveKeysRequest(BaseModel):
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    hf_api_key: str | None = None
    nanobanana_api_key: str | None = None


def mask_key(key: str | None) -> str | None:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


@router.get("/api/providers/keys")
async def get_providers_keys(current_user: dict = Depends(get_current_user)) -> dict:
    settings = get_settings()
    chat_db = ChatDatabase(settings)
    email = current_user.get("username")
    keys = chat_db.get_client_api_keys(email)
    return {
        "groq_api_key": mask_key(keys.get("groq_api_key")),
        "gemini_api_key": mask_key(keys.get("gemini_api_key")),
        "hf_api_key": mask_key(keys.get("hf_api_key")),
        "nanobanana_api_key": mask_key(keys.get("nanobanana_api_key")),
    }


@router.post("/api/providers/keys")
async def save_providers_keys(request: SaveKeysRequest, current_user: dict = Depends(get_current_user)) -> dict:
    settings = get_settings()
    chat_db = ChatDatabase(settings)
    email = current_user.get("username")
    
    existing = chat_db.get_client_api_keys(email)
    
    groq = request.groq_api_key
    if groq and ("..." in groq or groq.startswith("****")):
        groq = existing.get("groq_api_key")
        
    gemini = request.gemini_api_key
    if gemini and ("..." in gemini or gemini.startswith("****")):
        gemini = existing.get("gemini_api_key")
        
    hf = request.hf_api_key
    if hf and ("..." in hf or hf.startswith("****")):
        hf = existing.get("hf_api_key")
        
    nanobanana = request.nanobanana_api_key
    if nanobanana and ("..." in nanobanana or nanobanana.startswith("****")):
        nanobanana = existing.get("nanobanana_api_key")
        
    chat_db.save_client_api_keys(
        client_email=email,
        groq_key=groq,
        gemini_key=gemini,
        hf_key=hf,
        nanobanana_key=nanobanana
    )
    return {"status": "success", "message": "API keys successfully updated."}
