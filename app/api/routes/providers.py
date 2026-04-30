from fastapi import APIRouter
import httpx

from app.core.config import get_settings

router = APIRouter(tags=["providers"])


@router.get("/provider-health")
async def provider_health() -> dict:
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
