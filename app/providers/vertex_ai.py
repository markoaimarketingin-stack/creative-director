import asyncio
import base64
import binascii
from typing import Any
from vertexai.preview.vision_models import ImageGenerationModel, Image as VertexImage
import vertexai

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept


class VertexAIClient:
    _MAX_REFERENCE_IMAGES = 4

    def __init__(self, settings: Settings) -> None:
        self._project_id = settings.vertex_ai_project_id
        self._location = settings.vertex_ai_location
        self._model_name = settings.vertex_ai_image_model
        
        if self._project_id:
            vertexai.init(project=self._project_id, location=self._location)
            self._model = ImageGenerationModel.from_pretrained(self._model_name)
        else:
            self._model = None

    async def generate_batch(
        self,
        concepts: list[VisualConcept],
        *,
        platform: Platform,
        sample_images: list[str] | None = None
    ) -> list[GeneratedCreative]:
        tasks = [
            self.generate_creative(concept, platform=platform, sample_images=sample_images)
            for concept in concepts
        ]
        return await asyncio.gather(*tasks)

    async def generate_creative(
        self,
        concept: VisualConcept,
        *,
        platform: Platform,
        sample_images: list[str] | None = None
    ) -> GeneratedCreative:
        if not self._project_id or not self._model:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="vertex-ai",
                status=CreativeStatus.SKIPPED,
                prompt=concept.generation_prompt,
                error="VERTEX_AI_PROJECT_ID is not configured.",
            )

        last_error = "Vertex AI generation did not return a usable response."
        try:
            # Prepare context images if sample images are provided
            reference_images = []
            if sample_images:
                for img_data in sample_images[: self._MAX_REFERENCE_IMAGES]:
                    image_bytes = self._decode_sample_image(img_data)
                    if image_bytes:
                        reference_images.append(VertexImage(image_bytes))

            # Add context images to generation kwargs if supported by the model version.
            # Using loop.run_in_executor since vertexai SDK is synchronous.
            loop = asyncio.get_running_loop()
            
            kwargs = {
                "prompt": concept.generation_prompt,
                # "number_of_images": 1,
                "aspect_ratio": self._get_vertex_aspect_ratio(concept.aspect_ratio),
            }

            response = await self._generate_with_optional_references(
                loop=loop,
                kwargs=kwargs,
                reference_images=reference_images,
            )

            image_urls = []
            for result in getattr(response, "images", []):
                data_url = self._vertex_image_to_data_url(result)
                if data_url:
                    image_urls.append(data_url)
            
            if image_urls:
                return GeneratedCreative(
                    concept_id=concept.concept_id,
                    provider="vertex-ai",
                    provider_api_version=self._model_name,
                    status=CreativeStatus.GENERATED,
                    prompt=concept.generation_prompt,
                    image_urls=image_urls,
                    video_urls=[],
                    raw_response={
                        "urls": image_urls,
                        "reference_images_used": bool(reference_images),
                        "reference_image_count": len(reference_images),
                    },
                )
            
            last_error = "Vertex AI response did not include media."
        except Exception as exc:
            last_error = f"Vertex AI request failed: {exc}"

        return GeneratedCreative(
            concept_id=concept.concept_id,
            provider="vertex-ai",
            status=CreativeStatus.FAILED,
            prompt=concept.generation_prompt,
            error=last_error,
        )

    def _get_vertex_aspect_ratio(self, ratio_str: str) -> str:
        # Map generic like "16:9" to Vertex AI specific format (e.g. "16:9")
        return ratio_str

    async def _generate_with_optional_references(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        kwargs: dict[str, Any],
        reference_images: list[VertexImage],
    ) -> Any:
        if not reference_images:
            return await loop.run_in_executor(
                None,
                lambda: self._model.generate_images(**kwargs),
            )

        reference_kwargs = {**kwargs, "reference_images": reference_images}
        try:
            return await loop.run_in_executor(
                None,
                lambda: self._model.generate_images(**reference_kwargs),
            )
        except TypeError:
            # Older SDK/model combinations may not support reference_images.
            return await loop.run_in_executor(
                None,
                lambda: self._model.generate_images(**kwargs),
            )

    def _decode_sample_image(self, image_data: str) -> bytes | None:
        normalized = image_data.strip()
        if normalized.startswith("data:"):
            parts = normalized.split(",", 1)
            if len(parts) != 2:
                return None
            normalized = parts[1]
        if not normalized:
            return None
        try:
            return base64.b64decode(normalized, validate=True)
        except Exception:
            return None

    def _vertex_image_to_data_url(self, image_obj: Any) -> str | None:
        image_bytes = self._extract_image_bytes(image_obj)
        if not image_bytes:
            return None
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _extract_image_bytes(self, image_obj: Any) -> bytes | None:
        direct_bytes = getattr(image_obj, "_image_bytes", None)
        if isinstance(direct_bytes, bytes) and direct_bytes:
            return direct_bytes

        to_bytes = getattr(image_obj, "to_bytes", None)
        if callable(to_bytes):
            try:
                value = to_bytes()
                if isinstance(value, bytes) and value:
                    return value
            except Exception:
                pass

        as_base64 = getattr(image_obj, "_as_base64_string", None)
        if callable(as_base64):
            try:
                value = as_base64()
                if isinstance(value, str) and value.strip():
                    return base64.b64decode(value, validate=True)
            except (ValueError, binascii.Error):
                pass

        return None

    async def aclose(self) -> None:
        pass
