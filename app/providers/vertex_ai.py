import asyncio
import base64
import binascii
import aiohttp
import json
from typing import Any

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept


class VertexAIClient:
    _MAX_REFERENCE_IMAGES = 4

    def __init__(self, settings: Settings) -> None:
        self._project_id = settings.vertex_ai_project_id
        self._location = settings.vertex_ai_location
        self._model_name = settings.vertex_ai_image_model
        self._api_key = settings.google_api_key
        self._base_url = "https://us-central1-aiplatform.googleapis.com/v1"

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
        if not self._project_id or not self._api_key:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="vertex-ai",
                status=CreativeStatus.SKIPPED,
                prompt=concept.generation_prompt,
                error="VERTEX_AI_PROJECT_ID or GOOGLE_API_KEY is not configured.",
            )

        try:
            image_urls = await self._call_imagen_api(concept)
            
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
                    },
                )
            else:
                return GeneratedCreative(
                    concept_id=concept.concept_id,
                    provider="vertex-ai",
                    status=CreativeStatus.FAILED,
                    prompt=concept.generation_prompt,
                    error="No images returned from Vertex AI API",
                )
        
        except Exception as e:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="vertex-ai",
                status=CreativeStatus.FAILED,
                prompt=concept.generation_prompt,
                error=str(e),
            )

    async def _call_imagen_api(self, concept: VisualConcept) -> list[str]:
        """Call Vertex AI Imagen API via REST."""
        # Use Vertex AI REST API endpoint (not generativelanguage)
        url = (
            f"https://us-central1-aiplatform.googleapis.com/v1/projects/{self._project_id}/"
            f"locations/{self._location}/publishers/google/models/imagen-3.0-generate-001:predict"
        )
        
        # For direct API key access, we need to use it as a query parameter
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "instances": [
                {
                    "prompt": concept.generation_prompt,
                }
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": self._get_vertex_aspect_ratio(concept.aspect_ratio),
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Use API key as query parameter for Vertex AI API
                async with session.post(
                    f"{url}?key={self._api_key}",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._extract_image_urls(data)
                    else:
                        error_text = await resp.text()
                        raise Exception(f"Vertex AI API returned {resp.status}: {error_text}")
            
            except aiohttp.ClientError as e:
                raise Exception(f"Failed to call Vertex AI API: {e}")

    def _extract_image_urls(self, response: dict) -> list[str]:
        """Extract image URLs from Vertex AI API response."""
        urls = []
        try:
            # Vertex AI REST API returns predictions with base64 encoded images
            predictions = response.get("predictions", [])
            if not predictions:
                print(f"Warning: No predictions in response: {response}")
                return urls
                
            for prediction in predictions:
                if isinstance(prediction, dict):
                    # Try to get bytesBase64Encoded field
                    bytes_base64 = prediction.get("bytesBase64Encoded") or prediction.get("bytesBase64Encoded")
                    if not bytes_base64:
                        # Try alternative keys
                        for key in ["image", "imageBase64", "base64"]:
                            if key in prediction:
                                bytes_base64 = prediction[key]
                                break
                    
                    if bytes_base64:
                        data_url = f"data:image/png;base64,{bytes_base64}"
                        urls.append(data_url)
                elif isinstance(prediction, str):
                    # If it's already a base64 string
                    data_url = f"data:image/png;base64,{prediction}"
                    urls.append(data_url)
        except Exception as e:
            print(f"Error extracting image URLs: {e}")
        
        return urls

    def _get_vertex_aspect_ratio(self, aspect_ratio: str) -> str:
        """Map aspect ratio to Vertex AI format."""
        ratio_map = {
            "1:1": "1:1",
            "4:5": "4:5",
            "9:16": "9:16",
            "16:9": "16:9",
            "1.91:1": "1.91:1",
        }
        return ratio_map.get(aspect_ratio, "1:1")

    async def aclose(self) -> None:
        pass
