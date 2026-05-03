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
        self._reference_model = settings.hf_image_reference_model.strip()
        
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

        # Try primary model then small model for generation
        models_to_try = [self._primary_model]
        if self._small_model and self._small_model != self._primary_model:
            models_to_try.append(self._small_model)

        last_error = "Hugging Face generation did not return a usable response."
        
        for model in models_to_try:
            model_result = await self._generate_with_model(
                model=model,
                concept=concept,
                sample_images=None,
                use_reference_image=False,
            )
            if model_result:
                return model_result
            last_error = f"Hugging Face generation did not return a usable response for {model}."

        return GeneratedCreative(
            concept_id=concept.concept_id,
            provider="huggingface",
            status=CreativeStatus.FAILED,
            prompt=concept.generation_prompt,
            error=last_error,
        )

    async def _generate_with_model(
        self,
        *,
        model: str,
        concept: VisualConcept,
        sample_images: list[str] | None,
        use_reference_image: bool,
    ) -> GeneratedCreative | None:
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "*/*",
            }
            url = self._get_url(model)

            # Text-to-image generation
            prompt = f"{concept.generation_prompt} aspect ratio {concept.aspect_ratio}"
            payload = {"inputs": prompt}
            print(f"[INFO] HF text-to-image request to {model}: {prompt[:100]}...")

            response = await self._client.post(
                url,
                headers=headers,
                json=payload,
            )

            if response.status_code in (429, 503):
                print(f"[WARN] HF model {model} temporarily unavailable: {response.status_code}")
                return None

            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "image" not in content_type:
                preview = response.text[:300]
                print(f"[WARN] HF model {model} returned non-image: {response.status_code} {preview}")
                return None

            image_bytes = response.content
            if not image_bytes:
                print(f"[WARN] HF model {model} returned empty image bytes")
                return None

            encoded = base64.b64encode(image_bytes).decode("ascii")
            mime_type = "image/jpeg"
            if "png" in content_type:
                mime_type = "image/png"
            elif "webp" in content_type:
                mime_type = "image/webp"
            elif "gif" in content_type:
                mime_type = "image/gif"
            data_url = f"data:{mime_type};base64,{encoded}"
            
            print(f"[INFO] HF model {model} generated image successfully ({len(image_bytes)} bytes)")

            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="huggingface",
                provider_api_version=model,
                status=CreativeStatus.GENERATED,
                prompt=concept.generation_prompt,
                image_urls=[data_url],
                video_urls=[],
                raw_response={
                    "urls": [data_url],
                    "reference_image_used": False,
                },
            )
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            print(f"[ERROR] HF HTTP error {exc.response.status_code} for {model}: {body}")
            return None
        except Exception as exc:
            print(f"[ERROR] HF request failed for {model}: {exc}")
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
