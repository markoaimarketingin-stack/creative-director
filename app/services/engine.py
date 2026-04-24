import asyncio
import inspect
import re
from datetime import UTC, datetime

from app.core.config import Settings
from app.models import (
    CampaignPackage,
    CreativeAsset,
    CreativeInput,
    GeneratedCreative,
    Hook,
    MessagingAngle,
    Objective,
    Platform,
    VisualConcept,
)
from app.providers.groq_llm import GroqLLMProvider
from app.providers.nanobanana import NanoBananaClient
from app.providers.vertex_ai import VertexAIClient
from app.services.database import CampaignDatabase
from app.services.generators import AdCopyGenerator, HookGenerator, MessagingAngleGenerator, VisualConceptGenerator
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
    ) -> None:
        self._hook_generator = hook_generator
        self._angle_generator = angle_generator
        self._ad_copy_generator = ad_copy_generator
        self._visual_concept_generator = visual_concept_generator
        self._nanobanana_client = nanobanana_client
        self._vertex_client = vertex_client
        self._scoring_service = scoring_service
        self._storage = storage
        self._database = database

    async def generate_campaign(self, payload: CreativeInput) -> CampaignPackage:
        hooks_task = asyncio.create_task(self._hook_generator.generate(payload))
        angles_task = asyncio.create_task(self._angle_generator.generate(payload))
        hooks, angles = await asyncio.gather(hooks_task, angles_task)

        ad_copy_task = asyncio.create_task(self._ad_copy_generator.generate(payload, hooks, angles))
        concept_task = asyncio.create_task(self._visual_concept_generator.generate(payload, hooks, angles))
        ad_copies, visual_concepts = await asyncio.gather(ad_copy_task, concept_task)

        if self._vertex_client and getattr(self._vertex_client, "_project_id", None):
            generated_creatives = await self._vertex_client.generate_batch(
                visual_concepts,
                platform=payload.platform,
                sample_images=payload.sample_images,
            )
        else:
            generated_creatives = await self._nanobanana_client.generate_batch(
                visual_concepts,
                platform=payload.platform,
            )

        ad_copies = self._scoring_service.score_ad_copies(
            payload,
            visual_concepts,
            ad_copies,
            generated_creatives,
        )
        scored_creatives = self._scoring_service.score(
            payload,
            visual_concepts,
            ad_copies,
            generated_creatives,
        )

        campaign_name = payload.campaign_name or self._default_campaign_name(payload)
        campaign_slug = slugify(campaign_name)
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

        package = CampaignPackage(
            campaign_name=campaign_name,
            campaign_slug=campaign_slug,
            created_at=datetime.now(tz=UTC),
            input=payload,
            hooks=hooks,
            angles=angles,
            ad_copies=ad_copies,
            visual_concepts=visual_concepts,
            generated_creatives=generated_creatives,
            scored_creatives=scored_creatives,
            creative_assets=creative_assets,
        )
        output_directory = self._storage.save_package(package)
        package.output_directory = output_directory

        if self._database:
            self._database.save_campaign(package)

        return package

    def get_top_creatives(self, *, limit: int, platform: Platform | None):
        return self._storage.get_top_creatives(limit=limit, platform=platform)

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
                    generated_creative=generated_lookup[concept.concept_id],
                    score=score_lookup[concept.concept_id],
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

        self.engine = CreativeDirectorEngine(
            hook_generator=HookGenerator(llm),
            angle_generator=MessagingAngleGenerator(llm),
            ad_copy_generator=AdCopyGenerator(llm),
            visual_concept_generator=VisualConceptGenerator(llm),
            nanobanana_client=nanobanana,
            scoring_service=CreativeScoringService(),
            storage=storage,
            database=database,
            vertex_client=vertex_client,
        )
        self._closables = [llm, nanobanana, vertex_client]

    async def aclose(self) -> None:
        for resource in self._closables:
            close_method = getattr(resource, "aclose", None)
            if callable(close_method):
                result = close_method()
                if inspect.isawaitable(result):
                    await result


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "campaign"