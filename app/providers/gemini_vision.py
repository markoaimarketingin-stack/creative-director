import base64
import httpx
from typing import Optional
from app.core.config import Settings

class GeminiVisionProvider:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = "gemini-1.5-flash" # Fast and supports vision
        self._client = httpx.AsyncClient(timeout=60.0)

    async def describe_images(self, sample_images: list[str]) -> str:
        if not self._api_key or not sample_images:
            return ""

        # Just describe the first image for brevity/speed, or combine them
        # For now, let's take the first one
        img_data = sample_images[0]
        if img_data.startswith("data:"):
            img_data = img_data.split(",", 1)[1]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Describe this reference image in detail for an AI image generator. Focus on the subject, colors, lighting, materials, and composition. Keep it concise but descriptive. Output only the description."},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg", # Assuming jpeg/png, Gemini is flexible
                            "data": img_data
                        }
                    }
                ]
            }]
        }

        try:
            response = await self._client.post(url, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as he:
                # Log response body for diagnostics but avoid leaking the API key
                body = None
                try:
                    body = response.text
                except Exception:
                    body = "<unreadable response body>"
                print(f"[WARN] Gemini Vision request failed: status={response.status_code} url={url.split('?')[0]} body={body}")
                # If model not found (404) attempt to list available models to help debugging
                if response.status_code == 404:
                    try:
                        list_url = "https://generativelanguage.googleapis.com/v1beta/models"
                        list_res = await self._client.get(f"{list_url}?key={self._api_key}")
                        list_body = list_res.text if list_res is not None else ""
                        print(f"[WARN] Model list response (for debugging): status={list_res.status_code} body={list_body}")
                    except Exception as le:
                        print(f"[WARN] Failed to fetch model list: {le}")
                return ""

            data = response.json()
            # Robustly locate the description text in response
            description = ""
            try:
                # typical GL responses include 'candidates' with content -> parts
                description = data.get('candidates', [])[0].get('content', {}).get('parts', [])[0].get('text', '')
            except Exception:
                # Fallback: try other possible shapes
                if isinstance(data, dict):
                    # look for text anywhere
                    import json
                    s = json.dumps(data)
                    description = s[:400]

            return (description or "").strip()
        except Exception as e:
            # Non-HTTP related exceptions
            print(f"[WARN] Gemini Vision analysis failed: {e}")
            return ""

    async def close(self) -> None:
        await self._client.aclose()
