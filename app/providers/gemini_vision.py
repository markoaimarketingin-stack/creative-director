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
            response.raise_for_status()
            data = response.json()
            description = data['candidates'][0]['content']['parts'][0]['text']
            return description.strip()
        except Exception as e:
            print(f"[WARN] Gemini Vision analysis failed: {e}")
            return ""

    async def close(self) -> None:
        await self._client.aclose()
