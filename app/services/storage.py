import json
from importlib import import_module
from datetime import UTC
from pathlib import Path
from typing import Any

try:
    boto3 = import_module("boto3")
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None

from app.core.config import Settings
from app.models import CampaignPackage, Platform, TopCreativeItem, TopCreativesResponse


class CampaignStorage:
    def __init__(self, settings: Settings) -> None:
        self._output_root = settings.output_root
        self._output_root.mkdir(parents=True, exist_ok=True)
        self._s3_bucket_name = settings.s3_bucket_name
        self._s3_client = (
            boto3.client("s3", region_name=settings.s3_region)
            if settings.s3_bucket_name and boto3 is not None
            else None
        )

    def save_package(self, package: CampaignPackage) -> str:
        timestamp = package.created_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        campaign_dir = self._output_root / package.campaign_slug / timestamp
        campaign_dir.mkdir(parents=True, exist_ok=True)

        payloads = {
            "input.json": package.input.model_dump(mode="json"),
            "hooks.json": [item.model_dump(mode="json") for item in package.hooks],
            "angles.json": [item.model_dump(mode="json") for item in package.angles],
            "ad_copy.json": [item.model_dump(mode="json") for item in package.ad_copies],
            "visual_concepts.json": [item.model_dump(mode="json") for item in package.visual_concepts],
            "creative_scores.json": [item.model_dump(mode="json") for item in package.scored_creatives],
            "creatives.json": [item.model_dump(mode="json") for item in package.creative_assets],
            "campaign_manifest.json": {
                "campaign_name": package.campaign_name,
                "campaign_slug": package.campaign_slug,
                "created_at": package.created_at.isoformat(),
                "platform": package.input.platform.value,
                "objective": package.input.objective.value,
                "output_directory": str(campaign_dir),
            },
        }

        for filename, payload in payloads.items():
            file_path = campaign_dir / filename
            self._write_json(file_path, payload)
            self._mirror_to_s3(file_path=file_path, relative_key=file_path.relative_to(self._output_root))

        return str(campaign_dir)

    def get_top_creatives(
        self,
        *,
        limit: int = 10,
        platform: Platform | None = None,
    ) -> TopCreativesResponse:
        items: list[TopCreativeItem] = []

        for creatives_file in self._output_root.glob("*/*/creatives.json"):
            try:
                rows = json.loads(creatives_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            for row in rows:
                row_platform = row.get("platform")
                normalized_platform = self._parse_platform(row_platform)
                if platform and normalized_platform != platform:
                    continue
                score = row.get("score", {})
                generated = row.get("generated_creative", {})
                items.append(
                    TopCreativeItem(
                        campaign_name=row.get("campaign_name", creatives_file.parent.parent.name),
                        campaign_slug=row.get("campaign_slug", creatives_file.parent.parent.name),
                        platform=normalized_platform,
                        concept_id=row.get("concept_id", "unknown"),
                        total_score=score.get("total_score", 0),
                        headline=row.get("headline"),
                        cta=row.get("cta"),
                        image_urls=generated.get("image_urls", []),
                        video_urls=generated.get("video_urls", []),
                        output_directory=str(creatives_file.parent),
                    )
                )

        ranked = sorted(items, key=lambda item: item.total_score, reverse=True)
        return TopCreativesResponse(items=ranked[:limit])

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    def _mirror_to_s3(self, *, file_path: Path, relative_key: Path) -> None:
        if not self._s3_client or not self._s3_bucket_name:
            return
        self._s3_client.upload_file(str(file_path), self._s3_bucket_name, relative_key.as_posix())

    @staticmethod
    def _parse_platform(value: Any) -> Platform:
        if isinstance(value, Platform):
            return value
        if isinstance(value, str):
            try:
                return Platform(value)
            except ValueError:
                pass
        return Platform.META
