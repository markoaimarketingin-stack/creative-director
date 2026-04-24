import asyncio
import base64
from typing import Any
from vertexai.preview.vision_models import ImageGenerationModel, Image as VertexImage
import vertexai

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept


class VertexAIClient:
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
                for img_data in sample_images:
                    if img_data.startswith("data:"):
                        # Extract base64 part
                        img_data = img_data.split(",")[1]
                    image_bytes = base64.b64decode(img_data)
                    reference_images.append(VertexImage(image_bytes))

            # Add context images to generation kwargs if supported by the model version.
            # Using loop.run_in_executor since vertexai SDK is synchronous.
            loop = asyncio.get_running_loop()
            
            kwargs = {
                "prompt": concept.generation_prompt,
                # "number_of_images": 1,
                "aspect_ratio": self._get_vertex_aspect_ratio(concept.aspect_ratio),
            }

            # Uncomment below if using conditional parameters for image context or style overrides:
            # if reference_images:
            #     kwargs["reference_images"] = reference_images
            
            response = await loop.run_in_executor(
                None,
                lambda: self._model.generate_images(**kwargs)
            )

            image_urls = []
            for i, result in enumerate(response.images):
                # Optionally upload standard bytes to storage here; mock for now
                # In actual use, you'd save result._image_bytes to GCS or S3, then append URL
                # For demonstration, we simply label it as a generated local stub
                image_urls.append(f"vertex_generated_{concept.concept_id}_{i}.png")
            
            if image_urls:
                return GeneratedCreative(
                    concept_id=concept.concept_id,
                    provider="vertex-ai",
                    provider_api_version=self._model_name,
                    status=CreativeStatus.GENERATED,
                    prompt=concept.generation_prompt,
                    image_urls=image_urls,
                    video_urls=[],
                    raw_response={"urls": image_urls},
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

    async def aclose(self) -> None:
        pass
