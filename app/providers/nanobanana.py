import asyncio
import re
from typing import Any

import httpx

from app.core.config import Settings
from app.models import CreativeStatus, GeneratedCreative, Platform, VisualConcept

URL_RE = re.compile(r"^https?://", re.IGNORECASE)
VIDEO_HINT_RE = re.compile(r"\.(mp4|mov|webm)(\?|$)", re.IGNORECASE)
IMAGE_HINT_RE = re.compile(r"\.(png|jpe?g|webp|gif|avif)(\?|$)", re.IGNORECASE)


class NanoBananaClient:
    def __init__(self, settings: Settings) -> None:
        self._api_key = self._normalize_api_key(settings.nanobanana_api_key)
        self._base_url = settings.nanobanana_base_url.rstrip("/")
        self._default_model = settings.nanobanana_default_model
        self._image_size = settings.nanobanana_image_size
        self._preferred_version = settings.nanobanana_preferred_api_version.lower()
        self._poll_attempts = settings.nanobanana_poll_attempts
        self._poll_interval_seconds = settings.nanobanana_poll_interval_seconds
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(settings.nanobanana_timeout_seconds),
            follow_redirects=True,
            limits=limits,

        )

    async def generate_batch(
        self,
        concepts: list[VisualConcept],
        *,
        platform: Platform,
        sample_images: list[str] | None = None,
    ) -> list[GeneratedCreative]:
        tasks = [self.generate_creative(concept, platform=platform, sample_images=sample_images) for concept in concepts]
        return await asyncio.gather(*tasks)

    async def generate_creative(
        self,
        concept: VisualConcept,
        *,
        platform: Platform,
        sample_images: list[str] | None = None,
    ) -> GeneratedCreative:
        if not self._api_key:
            return GeneratedCreative(
                concept_id=concept.concept_id,
                provider="nanobanana",
                status=CreativeStatus.SKIPPED,
                prompt=concept.generation_prompt,
                error="NANOBANANA_API_KEY is not configured.",
            )

        last_error = "NanoBanana generation did not return a usable response."
        try:
            response = await self._client.post(
                "/generate",
                headers=self._headers(),
                json=self._build_generate_payload(concept, platform=platform),
            )
            response.raise_for_status()
            body = response.json()
            image_urls, video_urls = self._extract_media_urls(body)

            if not image_urls and not video_urls:
                task_id = self._extract_task_id(body)
                if task_id:
                    image_urls, video_urls, poll_error = await self._poll_for_result(task_id)
                    if poll_error:
                        last_error = poll_error

            if image_urls or video_urls:
                return GeneratedCreative(
                    concept_id=concept.concept_id,
                    provider="nanobanana",
                    provider_api_version="v1",
                    status=CreativeStatus.GENERATED,
                    prompt=concept.generation_prompt,
                    image_urls=image_urls,
                    video_urls=video_urls,
                    raw_response=body,
                )

            last_error = "NanoBanana response did not include media URLs."
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300]
            last_error = f"v1 HTTP error {exc.response.status_code}: {body}"
        except Exception as exc:  # pragma: no cover
            last_error = f"v1 request failed: {exc}"

        return GeneratedCreative(
            concept_id=concept.concept_id,
            provider="nanobanana",
            status=CreativeStatus.FAILED,
            prompt=concept.generation_prompt,
            error=last_error,
        )

    def _build_generate_payload(
        self,
        concept: VisualConcept,
        *,
        platform: Platform,
    ) -> dict[str, Any]:
        return {
            "prompt": concept.generation_prompt,
            "model": self._default_model,
            "aspectRatio": concept.aspect_ratio,
            "imageSize": self._image_size,
            "platform": platform.value,
            "taskType": "txt2img" if concept.media_type.value == "image" else "txt2video",
        }

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _poll_for_result(self, task_id: str) -> tuple[list[str], list[str], str | None]:
        for _ in range(self._poll_attempts):
            try:
                response = await self._client.get(
                    "/generate",
                    headers=self._headers(),
                    params={"id": task_id},
                )
                response.raise_for_status()
                body = response.json()
                image_urls, video_urls = self._extract_media_urls(body)
                if image_urls or video_urls:
                    return image_urls, video_urls, None
                status = str(self._extract_status(body)).lower()
                if status in {"failed", "error", "cancelled"}:
                    return [], [], f"NanoBanana task {task_id} finished with status '{status}'."
            except Exception:
                pass
            await asyncio.sleep(self._poll_interval_seconds)

        return [], [], f"NanoBanana task {task_id} did not produce media within the polling window."

    def _extract_media_urls(self, payload: Any) -> tuple[list[str], list[str]]:
        collected: list[tuple[str, str]] = []

        def walk(node: Any, path: str = "") -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    child_path = f"{path}.{key}" if path else key
                    if isinstance(value, str) and URL_RE.match(value):
                        collected.append((child_path.lower(), value))
                    else:
                        walk(value, child_path)
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f"{path}[{index}]")

        walk(payload)

        image_urls: list[str] = []
        video_urls: list[str] = []
        for path, value in collected:
            if "video" in path or VIDEO_HINT_RE.search(value):
                video_urls.append(value)
            elif "image" in path or IMAGE_HINT_RE.search(value):
                image_urls.append(value)
            else:
                image_urls.append(value)

        return self._unique(image_urls), self._unique(video_urls)

    def _extract_task_id(self, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("task_id", "taskId", "id", "taskIdOrId"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            for value in payload.values():
                task_id = self._extract_task_id(value)
                if task_id:
                    return task_id
        if isinstance(payload, list):
            for value in payload:
                task_id = self._extract_task_id(value)
                if task_id:
                    return task_id
        return None

    def _extract_status(self, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("status", "state", "processingStatus"):
                value = payload.get(key)
                if isinstance(value, str):
                    return value
            for value in payload.values():
                status = self._extract_status(value)
                if status:
                    return status
        if isinstance(payload, list):
            for value in payload:
                status = self._extract_status(value)
                if status:
                    return status
        return None

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _normalize_api_key(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if (
            len(normalized) >= 2
            and normalized[0] == normalized[-1]
            and normalized[0] in {"'", '"'}
        ):
            normalized = normalized[1:-1].strip()
        return normalized or None
