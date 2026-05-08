import asyncio
import base64
import binascii
import json
from typing import Any
import io
import os

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept

try:
    from google.cloud import aiplatform
    from google.cloud.aiplatform.generative_models import GenerativeModel, Part
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False


class VertexAIClient:
    _MAX_REFERENCE_IMAGES = 4

    def __init__(self, settings: Settings) -> None:
        self._project_id = settings.vertex_ai_project_id
        self._location = settings.vertex_ai_location
        self._model_name = settings.vertex_ai_image_model
        self._client = None
        
        # Initialize Vertex AI with project credentials
        if self._project_id and VERTEX_AI_AVAILABLE:
            try:
                print(f"[VERTEX_AI] Initializing with project: {self._project_id}, location: {self._location}")
                aiplatform.init(project=self._project_id, location=self._location)
                self._client = GenerativeModel("imagen-3.0-generate-001")
                print(f"[VERTEX_AI] ✅ Successfully initialized Vertex AI client")
            except Exception as e:
                print(f"[VERTEX_AI] ❌ Failed to initialize: {type(e).__name__}: {e}")
                self._client = None
        else:
            print(f"[VERTEX_AI] Skipped - VERTEX_AI_AVAILABLE={VERTEX_AI_AVAILABLE}, project_id={self._project_id}")

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
        if not self._project_id or not self._client:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="vertex-ai",
                status=CreativeStatus.SKIPPED,
                prompt=concept.generation_prompt,
                error="VERTEX_AI_PROJECT_ID not set or Google Cloud credentials not available. Set GOOGLE_APPLICATION_CREDENTIALS env var.",
            )

        try:
            image_urls = await self._call_imagen_api(concept, sample_images=sample_images)
            
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

    async def _call_imagen_api(self, concept: VisualConcept, sample_images: list[str] | None = None) -> list[str]:
        """Call Vertex AI Imagen API using the official SDK."""
        try:
            # Run SDK call in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._generate_images_sync,
                concept,
                sample_images
            )
            
            if response and hasattr(response, 'images') and response.images:
                urls = []
                for image in response.images:
                    # Save image to local file and return file URL
                    image_path = self._save_image_locally(image.data)
                    if image_path:
                        urls.append(f"/output/{image_path}")
                return urls
            else:
                return []
        
        except Exception as e:
            print(f"Vertex AI API error: {e}")
            raise Exception(f"Failed to call Vertex AI API: {e}")

    def _generate_images_sync(self, concept: VisualConcept, sample_images: list[str] | None = None):
        """Synchronous image generation using Vertex AI SDK with optional reference images."""
        try:
            # Prepare kwargs
            kwargs = {
                "prompt": concept.generation_prompt,
                "number_of_images": 1,
                "aspect_ratio": self._get_vertex_aspect_ratio(concept.aspect_ratio),
            }
            
            # Add reference images if provided (up to 4)
            if sample_images:
                reference_images = []
                for img_path in sample_images[:self._MAX_REFERENCE_IMAGES]:
                    try:
                        # Load image and convert to bytes
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                        reference_images.append(Part.from_data(img_data, mime_type="image/png"))
                    except Exception as e:
                        print(f"Failed to load reference image {img_path}: {e}")
                
                if reference_images:
                    kwargs["reference_images"] = reference_images
            
            response = self._client.generate_images(**kwargs)
            return response
        except Exception as e:
            print(f"Vertex AI generation failed: {e}")
            raise

    def _save_image_locally(self, image_data: bytes) -> str | None:
        """Save image to local output directory and return relative path."""
        try:
            from datetime import datetime
            import hashlib
            
            # Create output directory
            output_dir = "output/vertex_ai_images"
            os.makedirs(output_dir, exist_ok=True)
            
            # Create filename from timestamp and hash
            timestamp = datetime.now().isoformat().replace(':', '-')
            content_hash = hashlib.md5(image_data).hexdigest()[:8]
            filename = f"imagen_{timestamp}_{content_hash}.png"
            
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            return f"vertex_ai_images/{filename}"
        except Exception as e:
            print(f"Failed to save image locally: {e}")
            return None

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
