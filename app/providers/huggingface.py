import asyncio
import base64
from typing import Any

import httpx

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept


class HuggingFaceClient:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.hf_api_key.strip() if settings.hf_api_key else settings.hf_api_key
        self._primary_model = settings.hf_image_model.strip()
        self._small_model = settings.hf_image_model_small.strip()
        
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            follow_redirects=True,
            limits=limits,
        )

    def _get_url(self, model: str) -> str:
        return f"https://router.huggingface.co/hf-inference/models/{model}"

    async def generate_batch(
        self,
        concepts: list[VisualConcept],
        *,
        platform: Platform,
        sample_images: list[str] | None = None,
    ) -> list[GeneratedCreative]:
        tasks = [self.generate_creative(concept, sample_images=sample_images) for concept in concepts]
        return await asyncio.gather(*tasks)

    async def generate_creative(
        self,
        concept: VisualConcept,
        *,
        sample_images: list[str] | None = None,
    ) -> GeneratedCreative:
        if not self._api_key:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="huggingface",
                status=CreativeStatus.SKIPPED,
                prompt=concept.generation_prompt,
                error="HF_API_KEY is not configured.",
            )

        # Try primary model then small model
        models_to_try = [self._primary_model]
        if self._small_model and self._small_model != self._primary_model:
            models_to_try.append(self._small_model)

        last_error = "Hugging Face generation did not return a usable response."
        
        for model in models_to_try:
            try:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "*/*",
                }
                # Add aspect ratio hint to the prompt for models like Flux
                prompt = f"{concept.generation_prompt} aspect ratio {concept.aspect_ratio}"
                payload = {"inputs": prompt}
                url = self._get_url(model)
                
                response = await self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                
                # If model is loading (503), we might want to wait or try small model
                # But for simplicity, if it's 503 or 429, we just move to the next model
                if response.status_code in (429, 503) and model != models_to_try[-1]:
                    await asyncio.sleep(1.2)
                    continue
                    
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "image" not in content_type:
                    preview = response.text[:300]
                    last_error = f"Hugging Face non-image response from {model}: {preview}"
                    continue

                image_bytes = response.content
                if image_bytes:
                    encoded = base64.b64encode(image_bytes).decode("ascii")
                    mime_type = "image/jpeg"
                    if "png" in content_type:
                        mime_type = "image/png"
                    elif "webp" in content_type:
                        mime_type = "image/webp"
                    elif "gif" in content_type:
                        mime_type = "image/gif"
                    data_url = f"data:{mime_type};base64,{encoded}"
                    
                    return GeneratedCreative(
                        concept_id=concept.concept_id,
                        provider="huggingface",
                        provider_api_version=model,
                        status=CreativeStatus.GENERATED,
                        prompt=concept.generation_prompt,
                        image_urls=[data_url],
                        video_urls=[],
                        raw_response={"urls": [data_url]},
                    )
                
                last_error = f"Hugging Face response from {model} did not include media."
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:300]
                last_error = f"Hugging Face HTTP error {exc.response.status_code} for {model}: {body}"
                if exc.response.status_code in (429, 503) and model != models_to_try[-1]:
                    continue
            except Exception as exc:
                last_error = f"Hugging Face request failed for {model}: {exc}"

        return GeneratedCreative(
            concept_id=concept.concept_id,
            provider="huggingface",
            status=CreativeStatus.FAILED,
            prompt=concept.generation_prompt,
            error=last_error,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
