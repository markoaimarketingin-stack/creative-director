import asyncio
import inspect
import re
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.models import (
    CampaignPackage,
    CreativeAsset,
    CreativeInput,
    CreativeStatus,
    GeneratedCreative,
    Hook,
    MessagingAngle,
    Objective,
    Platform,
    VisualConcept,
)
from app.providers.gemini_vision import GeminiVisionProvider
from app.providers.groq_llm import GroqLLMProvider
from app.providers.huggingface import HuggingFaceClient
from app.providers.nanobanana import NanoBananaClient
from app.providers.vertex_ai import VertexAIClient
from app.services.composition import AdCompositionService, build_brand_assets
from app.services.database import CampaignDatabase
from app.services.exporter import MetaAdsCsvExporter
from app.services.generators import AdCopyGenerator, HookGenerator, MessagingAngleGenerator, VisualConceptGenerator
from app.services.image_fallback import LocalImageFallbackService
from app.services.preview import AdPreviewGenerator
from app.services.scoring import CreativeScoringService
from app.services.storage import CampaignStorage


class CreativeDirectorEngine:
    def __init__(
        self,
        *,
        hook_generator: HookGenerator,
        angle_generator: MessagingAngleGenerator,
        ad_copy_generator: AdCopyGenerator,
        visual_concept_generator: VisualConceptGenerator,
        nanobanana_client: NanoBananaClient,
        scoring_service: CreativeScoringService,
        storage: CampaignStorage,
        database: CampaignDatabase | None = None,
        vertex_client: VertexAIClient | None = None,
        hf_client: HuggingFaceClient | None = None,
        composition_service: AdCompositionService | None = None,
        preview_generator: AdPreviewGenerator | None = None,
        exporter: MetaAdsCsvExporter | None = None,
        image_fallback_service: LocalImageFallbackService | None = None,
        gemini_vision: GeminiVisionProvider | None = None,
    ) -> None:
        self._hook_generator = hook_generator
        self._angle_generator = angle_generator
        self._ad_copy_generator = ad_copy_generator
        self._visual_concept_generator = visual_concept_generator
        self._nanobanana_client = nanobanana_client
        self._vertex_client = vertex_client
        self._hf_client = hf_client
        self._gemini_vision = gemini_vision
        self._scoring_service = scoring_service
        self._storage = storage
        self._database = database
        self._composition_service = composition_service
        self._preview_generator = preview_generator
        self._exporter = exporter
        self._image_fallback_service = image_fallback_service
        self._image_provider_timeout_seconds = 90.0

    async def generate_campaign(self, payload: CreativeInput) -> CampaignPackage:
        hooks_task = asyncio.create_task(self._hook_generator.generate(payload))
        angles_task = asyncio.create_task(self._angle_generator.generate(payload))
        hooks, angles = await asyncio.gather(hooks_task, angles_task)

        ad_copy_task = asyncio.create_task(self._ad_copy_generator.generate(payload, hooks, angles))
        concept_task = asyncio.create_task(self._visual_concept_generator.generate(payload, hooks, angles))
        ad_copies, visual_concepts = await asyncio.gather(ad_copy_task, concept_task)

        # 🚀 NEW: Analyze reference images using Gemini Vision if provided
        if payload.sample_images and self._gemini_vision:
            print(f"[INFO] Analyzing {len(payload.sample_images)} reference images...")
            description = await self._gemini_vision.describe_images(payload.sample_images)
            if description:
                print(f"[INFO] Visual Reference: {description[:100]}...")
                for concept in visual_concepts:
                    concept.generation_prompt += f" Visual Reference style: {description}"

        generated_creatives = []
        if self._vertex_client and getattr(self._vertex_client, "_project_id", None):
            generated_creatives = await self._generate_images_with_timeout(
                self._vertex_client.generate_batch(
                    visual_concepts,
                    platform=payload.platform,
                    sample_images=payload.sample_images,
                )
            )

        if not generated_creatives or any(c.status in (CreativeStatus.FAILED, CreativeStatus.SKIPPED) for c in generated_creatives):
            if self._nanobanana_client and self._has_real_api_key(getattr(self._nanobanana_client, "_api_key", None)):
                fallback_creatives = await self._generate_images_with_timeout(
                    self._nanobanana_client.generate_batch(
                        visual_concepts,
                        platform=payload.platform,
                        sample_images=payload.sample_images,
                    )
                )
                if fallback_creatives:
                    generated_creatives = fallback_creatives

        if not generated_creatives or any(c.status in (CreativeStatus.FAILED, CreativeStatus.SKIPPED) for c in generated_creatives):
            if getattr(self, "_hf_client", None) and getattr(self._hf_client, "_api_key", None):
                fallback_creatives = await self._generate_images_with_timeout(
                    self._hf_client.generate_batch(
                        visual_concepts,
                        platform=payload.platform,
                        sample_images=payload.sample_images,
                    )
                )
                if fallback_creatives:
                    generated_creatives = fallback_creatives

        if not generated_creatives:
            generated_creatives = []

        if self._image_fallback_service:
            generated_creatives = self._image_fallback_service.generate_batch(
                payload=payload,
                concepts=visual_concepts,
                existing=generated_creatives,
            )

        scored_creatives = await self._scoring_service.score(
            payload,
            visual_concepts,
            ad_copies,
            generated_creatives,
        )
        ad_copies = await self._scoring_service.score_ad_copies(
            payload,
            visual_concepts,
            ad_copies,
            generated_creatives,
        )

        created_at = datetime.now(tz=UTC)
        campaign_name = payload.campaign_name or self._default_campaign_name(payload)
        campaign_slug = slugify(campaign_name)
        brand_assets = build_brand_assets(
            brand_name=payload.brand_name,
            logo_image=payload.logo_image,
            brand_colors=payload.brand_colors,
            brand_fonts=payload.brand_fonts,
        )
        campaign_dir = self._storage.build_campaign_dir(campaign_slug, created_at)
        creative_assets = self._build_creative_assets(
            campaign_name=campaign_name,
            campaign_slug=campaign_slug,
            platform=payload.platform,
            objective=payload.objective,
            hooks=hooks,
            angles=angles,
            ad_copies=ad_copies,
            visual_concepts=visual_concepts,
            generated_creatives=generated_creatives,
            scored_creatives=scored_creatives,
        )
        creative_assets = self._render_assets(
            creative_assets=creative_assets,
            campaign_dir=campaign_dir,
            brand_assets=brand_assets,
            brand_name=payload.brand_name,
        )
        export_rows = self._exporter.export(assets=creative_assets, campaign_dir=campaign_dir) if self._exporter else []

        package = CampaignPackage(
            campaign_name=campaign_name,
            campaign_slug=campaign_slug,
            created_at=created_at,
            input=payload,
            hooks=hooks,
            angles=angles,
            ad_copies=ad_copies,
            visual_concepts=visual_concepts,
            generated_creatives=generated_creatives,
            scored_creatives=scored_creatives,
            creative_assets=creative_assets,
            brand_assets=brand_assets,
            export_rows=export_rows,
        )
        output_directory = self._storage.save_package(package)
        package.output_directory = output_directory

        if self._database:
            self._database.save_campaign(package)

        return package

    async def _generate_images_with_timeout(self, coroutine):
        try:
            return await asyncio.wait_for(coroutine, timeout=self._image_provider_timeout_seconds)
        except Exception:
            return []

    @staticmethod
    def _has_real_api_key(value: str | None) -> bool:
        if not value:
            return False
        normalized = value.strip().lower()
        return "your_real_key_here" not in normalized and "placeholder" not in normalized

    def _render_assets(
        self,
        *,
        creative_assets: list[CreativeAsset],
        campaign_dir,
        brand_assets,
        brand_name: str,
    ) -> list[CreativeAsset]:
        rendered_assets: list[CreativeAsset] = []
        for asset in creative_assets:
            image_source = next(iter(asset.generated_creative.image_urls), None)
            if not image_source or not self._composition_service:
                rendered_assets.append(asset)
                continue

            rendered_ad = self._composition_service.compose_ad(
                image_source=image_source,
                primary_text=asset.primary_text or "",
                headline=asset.headline or asset.hook_text,
                description=asset.description or "",
                cta=asset.cta or "Learn More",
                brand_name=brand_name,
                brand_assets=brand_assets,
                concept_id=asset.concept_id,
                platform=asset.platform,
                aspect_ratio=asset.visual_concept.aspect_ratio,
                campaign_dir=campaign_dir,
            )
            
            updated_asset = asset.model_copy(update={"rendered_ad": rendered_ad})
            
            # Generate preview BEFORE normalizing paths
            if self._preview_generator:
                preview = self._preview_generator.generate(asset=updated_asset, campaign_dir=campaign_dir)
                updated_asset = updated_asset.model_copy(update={"preview": preview})
            
            # Normalize rendered path for frontend
            if rendered_ad.image_path:
                rel_path = Path(rendered_ad.image_path).relative_to(self._storage._output_root)
                rendered_ad.image_path = f"/output/{rel_path.as_posix()}"
                updated_asset = updated_asset.model_copy(update={"rendered_ad": rendered_ad})
                
            # Normalize preview path for frontend
            if updated_asset.preview and updated_asset.preview.image_path:
                rel_preview = Path(updated_asset.preview.image_path).relative_to(self._storage._output_root)
                preview = updated_asset.preview.model_copy(update={"image_path": f"/output/{rel_preview.as_posix()}"})
                updated_asset = updated_asset.model_copy(update={"preview": preview})
            rendered_assets.append(updated_asset)
        return rendered_assets

    def get_top_creatives(self, *, limit: int | None, platform: Platform | None):
        return self._storage.get_top_creatives(limit=limit, platform=platform)

    def get_campaign_history(self, *, limit: int | None, platform: Platform | None):
        return self._storage.get_campaign_history(limit=limit, platform=platform)


    def _build_creative_assets(
        self,
        *,
        campaign_name: str,
        campaign_slug: str,
        platform: Platform,
        objective: Objective,
        hooks: list[Hook],
        angles: list[MessagingAngle],
        ad_copies,
        visual_concepts: list[VisualConcept],
        generated_creatives: list[GeneratedCreative],
        scored_creatives,
    ) -> list[CreativeAsset]:
        hook_lookup = {hook.text: hook for hook in hooks}
        angle_lookup = {angle.name: angle for angle in angles}
        copy_lookup = {(copy.hook_text, copy.angle_name): copy for copy in ad_copies}
        generated_lookup = {creative.concept_id: creative for creative in generated_creatives}
        score_lookup = {score.concept_id: score for score in scored_creatives}

        assets: list[CreativeAsset] = []
        for concept in visual_concepts:
            copy = copy_lookup.get((concept.hook_text, concept.angle_name)) or ad_copies[0]
            hook = hook_lookup.get(concept.hook_text)
            angle = angle_lookup.get(concept.angle_name)
            generated = generated_lookup.get(concept.concept_id)
            score = score_lookup.get(concept.concept_id)
            if generated is None or score is None:
                continue
            assets.append(
                CreativeAsset(
                    campaign_name=campaign_name,
                    campaign_slug=campaign_slug,
                    platform=platform,
                    objective=objective,
                    concept_id=concept.concept_id,
                    hook_type=hook.type if hook else None,
                    hook_text=concept.hook_text,
                    angle_name=concept.angle_name,
                    target_emotion=angle.target_emotion if angle else None,
                    primary_text=copy.primary_text,
                    headline=copy.headline,
                    description=copy.description,
                    cta=copy.cta,
                    visual_concept=concept,
                    generated_creative=generated,
                    score=score,
                )
            )
        assets.sort(key=lambda item: item.score.total_score, reverse=True)
        return assets

    @staticmethod
    def _default_campaign_name(payload: CreativeInput) -> str:
        return f"{payload.brand_name} {payload.objective.value} {payload.platform.value}"


class ServiceContainer:
    def __init__(self, settings: Settings) -> None:
        llm = GroqLLMProvider(settings)
        nanobanana = NanoBananaClient(settings)
        storage = CampaignStorage(settings)
        database = CampaignDatabase(settings)
        vertex_client = VertexAIClient(settings)
        hf_client = HuggingFaceClient(settings)
        gemini_vision = GeminiVisionProvider(settings)
        composition_service = AdCompositionService(settings.output_root)
        preview_generator = AdPreviewGenerator()
        exporter = MetaAdsCsvExporter()
        image_fallback_service = LocalImageFallbackService()

        self.engine = CreativeDirectorEngine(
            hook_generator=HookGenerator(llm),
            angle_generator=MessagingAngleGenerator(llm),
            ad_copy_generator=AdCopyGenerator(llm),
            visual_concept_generator=VisualConceptGenerator(llm),
            nanobanana_client=nanobanana,
            scoring_service=CreativeScoringService(llm),
            storage=storage,
            database=database,
            vertex_client=vertex_client,
            hf_client=hf_client,
            composition_service=composition_service,
            preview_generator=preview_generator,
            exporter=exporter,
            image_fallback_service=image_fallback_service,
            gemini_vision=gemini_vision,
        )
        self.engine._image_provider_timeout_seconds = settings.image_provider_timeout_seconds
        self._closables = [llm, nanobanana, vertex_client, hf_client, database, gemini_vision]

    async def aclose(self) -> None:
        for resource in self._closables:
            close_method = getattr(resource, "aclose", None)
            if callable(close_method):
                result = close_method()
                if inspect.isawaitable(result):
                    await result
                continue
            sync_close = getattr(resource, "close", None)
            if callable(sync_close):
                sync_close()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "campaign"
