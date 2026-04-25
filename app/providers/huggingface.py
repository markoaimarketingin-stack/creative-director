import asyncio
import base64
from typing import Any

import httpx

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept


class HuggingFaceClient:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.hf_api_key
        self._model = settings.hf_image_model
        self._base_url = f"https://api-inference.huggingface.co/models/{self._model}"
        
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            follow_redirects=True,
            limits=limits,
        )

    async def generate_batch(
        self,
        concepts: list[VisualConcept],
        *,
        platform: Platform,
    ) -> list[GeneratedCreative]:
        tasks = [self.generate_creative(concept) for concept in concepts]
        return await asyncio.gather(*tasks)

    async def generate_creative(
        self,
        concept: VisualConcept,
    ) -> GeneratedCreative:
        if not self._api_key:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="huggingface",
                status=CreativeStatus.SKIPPED,
                prompt=concept.generation_prompt,
                error="HF_API_KEY is not configured.",
            )

        last_error = "Hugging Face generation did not return a usable response."
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"}
            payload = {"inputs": concept.generation_prompt}
            
            response = await self._client.post(
                self._base_url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            
            image_bytes = response.content
            if image_bytes:
                encoded = base64.b64encode(image_bytes).decode("ascii")
                data_url = f"data:image/jpeg;base64,{encoded}"
                
                return GeneratedCreative(
                    concept_id=concept.concept_id,
                    provider="huggingface",
                    provider_api_version=self._model,
                    status=CreativeStatus.GENERATED,
                    prompt=concept.generation_prompt,
                    image_urls=[data_url],
                    video_urls=[],
                    raw_response={"urls": [data_url]},
                )
            
            last_error = "Hugging Face response did not include media."
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            last_error = f"Hugging Face HTTP error {exc.response.status_code}: {body}"
        except Exception as exc:
            last_error = f"Hugging Face request failed: {exc}"

        return GeneratedCreative(
            concept_id=concept.concept_id,
            provider="huggingface",
            status=CreativeStatus.FAILED,
            prompt=concept.generation_prompt,
            error=last_error,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
