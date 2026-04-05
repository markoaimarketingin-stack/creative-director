from collections import OrderedDict

from app.models import (
    AdCopy,
    CreativeInput,
    Hook,
    MessagingAngle,
    Platform,
    VisualConcept,
    VisualConceptDraft,
)
from app.providers.groq_llm import GroqLLMProvider
from app.services.groq_normalizer import (
    normalize_ad_copy_set,
    normalize_angle_set,
    normalize_hook_set,
    normalize_visual_concept_set,
)
from app.services.prompts import (
    CREATIVE_SYSTEM_PROMPT,
    PLATFORM_ASPECT_RATIOS,
    PLATFORM_COPY_LIMITS,
    ad_copy_prompt,
    angle_prompt,
    hook_prompt,
    nanobanana_prompt,
    visual_concept_prompt,
)


class HookGenerator:
    def __init__(self, llm: GroqLLMProvider) -> None:
        self._llm = llm

    async def generate(self, payload: CreativeInput) -> list[Hook]:
        raw_result = await self._llm.json_completion(
            instructions=CREATIVE_SYSTEM_PROMPT,
            user_prompt=hook_prompt(payload),
        )
        result = normalize_hook_set(raw_result)
        hooks = _dedupe_by_text(result.hooks, key=lambda item: item.text)
        return hooks[: payload.hook_count]


class MessagingAngleGenerator:
    def __init__(self, llm: GroqLLMProvider) -> None:
        self._llm = llm

    async def generate(self, payload: CreativeInput) -> list[MessagingAngle]:
        raw_result = await self._llm.json_completion(
            instructions=CREATIVE_SYSTEM_PROMPT,
            user_prompt=angle_prompt(payload),
        )
        result = normalize_angle_set(raw_result)
        angles = _dedupe_by_text(result.angles, key=lambda item: item.name)
        return angles[: payload.angle_count]


class AdCopyGenerator:
    def __init__(self, llm: GroqLLMProvider) -> None:
        self._llm = llm

    async def generate(
        self,
        payload: CreativeInput,
        hooks: list[Hook],
        angles: list[MessagingAngle],
    ) -> list[AdCopy]:
        raw_result = await self._llm.json_completion(
            instructions=CREATIVE_SYSTEM_PROMPT,
            user_prompt=ad_copy_prompt(payload, hooks, angles),
        )
        result = normalize_ad_copy_set(raw_result)

        limits = PLATFORM_COPY_LIMITS[payload.platform]
        normalized: list[AdCopy] = []
        for index, item in enumerate(result.ad_copies, start=1):
            normalized.append(
                AdCopy(
                    copy_id=f"copy-{index:02d}",
                    hook_text=item.hook_text,
                    angle_name=item.angle_name,
                    primary_text=_trim(item.primary_text, limits["primary_text"]),
                    headline=_trim(item.headline, limits["headline"]),
                    cta=_trim(item.cta, 24),
                    description=_trim(item.description, limits["description"]),
                )
            )

        return normalized[: payload.copy_count]


class VisualConceptGenerator:
    def __init__(self, llm: GroqLLMProvider) -> None:
        self._llm = llm

    async def generate(
        self,
        payload: CreativeInput,
        hooks: list[Hook],
        angles: list[MessagingAngle],
    ) -> list[VisualConcept]:
        raw_result = await self._llm.json_completion(
            instructions=CREATIVE_SYSTEM_PROMPT,
            user_prompt=visual_concept_prompt(payload, hooks, angles),
        )
        result = normalize_visual_concept_set(raw_result)

        concepts: list[VisualConcept] = []
        for index, item in enumerate(result.visual_concepts[: payload.concept_count], start=1):
            draft = _normalize_visual_concept(item, platform=payload.platform)
            concepts.append(
                VisualConcept(
                    concept_id=f"concept-{index:02d}",
                    hook_text=draft.hook_text,
                    angle_name=draft.angle_name,
                    scene_description=draft.scene_description,
                    camera_angle=draft.camera_angle,
                    background_setting=draft.background_setting,
                    color_palette=draft.color_palette,
                    mood=draft.mood,
                    style_reference=draft.style_reference,
                    aspect_ratio=draft.aspect_ratio,
                    media_type=draft.media_type,
                    generation_prompt=nanobanana_prompt(payload, draft),
                )
            )
        return concepts


def _normalize_visual_concept(draft: VisualConceptDraft, *, platform: Platform) -> VisualConceptDraft:
    allowed_aspects = PLATFORM_ASPECT_RATIOS[platform]
    aspect_ratio = draft.aspect_ratio if draft.aspect_ratio in allowed_aspects else allowed_aspects[0]
    return VisualConceptDraft(
        hook_text=draft.hook_text,
        angle_name=draft.angle_name,
        scene_description=draft.scene_description,
        camera_angle=draft.camera_angle,
        background_setting=draft.background_setting,
        color_palette=draft.color_palette[:5],
        mood=draft.mood,
        style_reference=draft.style_reference,
        aspect_ratio=aspect_ratio,
        media_type=draft.media_type,
    )


def _trim(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: max(limit - 3, 1)].rstrip() + "..."


def _dedupe_by_text(items: list, *, key):
    ordered = OrderedDict()
    for item in items:
        token = key(item).strip().lower()
        if token not in ordered:
            ordered[token] = item
    return list(ordered.values())
