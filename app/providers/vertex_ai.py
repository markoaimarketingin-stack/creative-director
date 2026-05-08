import asyncio
import base64
import binascii
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept

ImageGenerationModel = None
RawReferenceImage = None
VertexImage = None
aiplatform = None
VERTEX_AI_AVAILABLE = False
VERTEX_AI_IMPORT_ERROR = None

try:
    from vertexai.preview.vision_models import Image as VertexImage
    from vertexai.preview.vision_models import ImageGenerationModel, RawReferenceImage
    from google.cloud import aiplatform

    VERTEX_AI_AVAILABLE = True
except ImportError as e:
    try:
        # Fallback path for older/newer SDK layout changes.
        from vertexai.vision_models import Image as VertexImage
        from vertexai.vision_models import ImageGenerationModel, RawReferenceImage
        from google.cloud import aiplatform

        VERTEX_AI_AVAILABLE = True
    except ImportError as e2:
        VERTEX_AI_IMPORT_ERROR = f"{e}; fallback failed: {e2}"
        print(f"[VERTEX_AI] Import failed: {VERTEX_AI_IMPORT_ERROR}")


class VertexAIClient:
    def __init__(self, settings: Settings) -> None:
        self._project_id = settings.vertex_ai_project_id
        self._location = settings.vertex_ai_location
        self._model_name = settings.vertex_ai_image_model
        self._client = None

        if self._project_id and VERTEX_AI_AVAILABLE:
            try:
                print(f"[VERTEX_AI] Initializing with project={self._project_id}, location={self._location}")
                aiplatform.init(project=self._project_id, location=self._location)
                self._client = ImageGenerationModel.from_pretrained(self._model_name)
                print("[VERTEX_AI] Initialized Vertex AI Imagen client")
            except Exception as e:
                print(f"[VERTEX_AI] Failed to initialize: {type(e).__name__}: {e}")
                self._client = None
        else:
            print(
                "[VERTEX_AI] Skipped - "
                f"VERTEX_AI_AVAILABLE={VERTEX_AI_AVAILABLE}, "
                f"project_id={self._project_id}, "
                f"import_error={VERTEX_AI_IMPORT_ERROR}"
            )

    async def generate_batch(
        self,
        concepts: list[VisualConcept],
        *,
        platform: Platform,
        sample_images: list[str] | None = None,
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
        sample_images: list[str] | None = None,
    ) -> GeneratedCreative:
        if not self._project_id or not self._client:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="vertex-ai",
                status=CreativeStatus.SKIPPED,
                prompt=concept.generation_prompt,
                error=(
                    "Vertex AI unavailable. Check VERTEX_AI_PROJECT_ID, credentials, "
                    "and google-cloud-aiplatform/vertexai package compatibility."
                ),
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
                    raw_response={"urls": image_urls},
                )
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
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._generate_images_sync, concept, sample_images)
        images = getattr(response, "images", None)
        if not images:
            return []
        urls: list[str] = []
        for image in images:
            image_bytes = getattr(image, "_image_bytes", None) or getattr(image, "data", None)
            if not image_bytes:
                continue
            image_path = self._save_image_locally(image_bytes)
            if image_path:
                urls.append(f"/output/{image_path}")
        return urls

    def _generate_images_sync(self, concept: VisualConcept, sample_images: list[str] | None = None):
        kwargs = {
            "prompt": concept.generation_prompt,
            "number_of_images": 1,
            "aspect_ratio": self._get_vertex_aspect_ratio(concept.aspect_ratio),
        }
        if sample_images:
            references = self._build_reference_images(sample_images)
            if references:
                print(f"[VERTEX_AI] Using {len(references)} style reference image(s)")
                try:
                    # edit_image supports reference_images in the current SDK path.
                    return self._client.edit_image(
                        prompt=concept.generation_prompt,
                        reference_images=references,
                        number_of_images=1,
                    )
                except Exception as exc:
                    print(f"[VERTEX_AI] edit_image with references failed, fallback to text-only generation: {exc}")
        return self._client.generate_images(**kwargs)

    def _build_reference_images(self, sample_images: list[str]) -> list[RawReferenceImage]:
        references: list[RawReferenceImage] = []
        for index, source in enumerate(sample_images[:3], start=1):
            try:
                image_bytes = self._read_reference_source(source)
                vertex_image = VertexImage(image_bytes=image_bytes)
                # Vertex reference_id must be numeric for this endpoint.
                references.append(RawReferenceImage(reference_id=index, image=vertex_image))
            except Exception as exc:
                print(f"[VERTEX_AI] Failed to parse reference image {index}: {exc}")
        return references

    def _read_reference_source(self, source: str) -> bytes:
        if source.startswith("data:"):
            encoded = source.split(",", 1)[1]
            try:
                return base64.b64decode(encoded)
            except (binascii.Error, ValueError) as exc:
                raise ValueError(f"Invalid base64 data URL: {exc}") from exc

        if source.startswith("/output/"):
            relative = source[len("/output/"):].lstrip("/")
            output_path = Path("output") / relative
            if output_path.exists():
                return output_path.read_bytes()

        path = Path(source)
        if path.exists():
            return path.read_bytes()

        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            response = httpx.get(source, timeout=20.0, follow_redirects=True)
            response.raise_for_status()
            return response.content

        raise ValueError(f"Unsupported reference image source: {source}")

    def _save_image_locally(self, image_data: bytes) -> str | None:
        try:
            from datetime import datetime
            import hashlib

            output_dir = Path("output") / "vertex_ai_images"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().isoformat().replace(":", "-")
            content_hash = hashlib.md5(image_data).hexdigest()[:8]
            filename = f"imagen_{timestamp}_{content_hash}.png"
            filepath = output_dir / filename
            filepath.write_bytes(image_data)
            return f"vertex_ai_images/{filename}"
        except Exception as e:
            print(f"[VERTEX_AI] Failed to save image locally: {e}")
            return None

    def _get_vertex_aspect_ratio(self, aspect_ratio: str) -> str:
        ratio_map = {
            "1:1": "1:1",
            # Vertex Imagen in current SDK path may reject 4:5; use vertical-safe fallback.
            "4:5": "9:16",
            "9:16": "9:16",
            "16:9": "16:9",
            "1.91:1": "1.91:1",
        }
        return ratio_map.get(aspect_ratio, "9:16")

    async def aclose(self) -> None:
        return None
