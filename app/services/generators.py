import re
from collections import OrderedDict, defaultdict

from app.models import (
    AdCopy,
    CreativeInput,
    Hook,
    HookType,
    MediaType,
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
        try:
            raw_result = await self._llm.json_completion(
                instructions=CREATIVE_SYSTEM_PROMPT,
                user_prompt=hook_prompt(payload),
            )
            result = normalize_hook_set(raw_result)
        except Exception:
            result = type("HookResult", (), {"hooks": _fallback_hooks(payload)})()
        hooks = _enforce_hook_diversity(_dedupe_by_text(result.hooks, key=lambda item: item.text), payload.hook_count)
        return hooks[: payload.hook_count]


class MessagingAngleGenerator:
    def __init__(self, llm: GroqLLMProvider) -> None:
        self._llm = llm

    async def generate(self, payload: CreativeInput) -> list[MessagingAngle]:
        try:
            raw_result = await self._llm.json_completion(
                instructions=CREATIVE_SYSTEM_PROMPT,
                user_prompt=angle_prompt(payload),
            )
            result = normalize_angle_set(raw_result)
        except Exception:
            result = type("AngleResult", (), {"angles": _fallback_angles(payload)})()
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
        try:
            raw_result = await self._llm.json_completion(
                instructions=CREATIVE_SYSTEM_PROMPT,
                user_prompt=ad_copy_prompt(payload, hooks, angles),
            )
            result = normalize_ad_copy_set(raw_result)
        except Exception:
            result = type("CopyResult", (), {"ad_copies": _fallback_ad_copies(payload, hooks, angles)})()

        limits = PLATFORM_COPY_LIMITS[payload.platform]
        normalized: list[AdCopy] = []
        for index, item in enumerate(result.ad_copies, start=1):
            normalized.append(
                AdCopy(
                    copy_id=f"copy-{index:02d}",
                    hook_text=item.hook_text,
                    angle_name=item.angle_name,
                    primary_text=smart_truncate(item.primary_text, limits["primary_text"]),
                    headline=smart_truncate(item.headline, limits["headline"]),
                    cta=smart_truncate(item.cta, 24),
                    description=smart_truncate(item.description, limits["description"]),
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
        try:
            raw_result = await self._llm.json_completion(
                instructions=CREATIVE_SYSTEM_PROMPT,
                user_prompt=visual_concept_prompt(payload, hooks, angles),
            )
            result = normalize_visual_concept_set(raw_result)
        except Exception:
            result = type("ConceptResult", (), {"visual_concepts": _fallback_visual_concepts(payload, hooks, angles)})()

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


def smart_truncate(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact

    sentences = re.split(r"(?<=[.!?])\s+", compact)
    kept_sentences: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*kept_sentences, sentence]).strip()
        if candidate and len(candidate) <= limit:
            kept_sentences.append(sentence)
            continue
        break

    if kept_sentences:
        return " ".join(kept_sentences)

    words = compact.split()
    output: list[str] = []
    for word in words:
        candidate = " ".join([*output, word]).strip()
        if len(candidate) <= limit:
            output.append(word)
            continue
        break

    if not output:
        return compact[:limit].rstrip()
    return " ".join(output)


def _dedupe_by_text(items: list, *, key):
    ordered = OrderedDict()
    for item in items:
        token = key(item).strip().lower()
        if token not in ordered:
            ordered[token] = item
    return list(ordered.values())


def _enforce_hook_diversity(hooks: list[Hook], target_count: int) -> list[Hook]:
    buckets: dict[HookType, list[Hook]] = defaultdict(list)
    for hook in hooks:
        buckets[hook.type].append(hook)

    ordered_types = [
        HookType.CURIOSITY,
        HookType.FEAR_BASED,
        HookType.BENEFIT_DRIVEN,
        HookType.CONTRARIAN,
        HookType.SOCIAL_PROOF,
    ]

    diversified: list[Hook] = []
    round_index = 0
    while len(diversified) < target_count:
        added_this_round = False
        for hook_type in ordered_types:
            if round_index < len(buckets[hook_type]):
                diversified.append(buckets[hook_type][round_index])
                added_this_round = True
                if len(diversified) == target_count:
                    break
        if not added_this_round:
            break
        round_index += 1

    return diversified or hooks[:target_count]


def _fallback_hooks(payload: CreativeInput) -> list[Hook]:
    benefit = payload.key_benefits[0]
    brand = payload.brand_name
    product = payload.product_description.split(".")[0]
    templates = [
        (HookType.CURIOSITY, f"Why are in-house marketers switching to {brand} before launching a new campaign?"),
        (HookType.FEAR_BASED, f"Still shipping one ad angle at a time? That delay costs you paid traffic momentum."),
        (HookType.BENEFIT_DRIVEN, f"Build more winning ads in minutes, not all afternoon."),
        (HookType.CONTRARIAN, f"The best-performing ad system is not another prompt library. It is a production workflow."),
        (HookType.SOCIAL_PROOF, f"Growth teams use systems like {brand} when they need more creative volume without hiring."),
        (HookType.CURIOSITY, f"What changes when your team can turn one product brief into launch-ready ads?"),
        (HookType.FEAR_BASED, f"Generic hooks make cold traffic scroll past before your value prop lands."),
        (HookType.BENEFIT_DRIVEN, f"{benefit} with copy, concepts, and ready-to-review assets in one run."),
        (HookType.CONTRARIAN, f"Pretty concept boards do not scale performance. Finished creatives do."),
        (HookType.SOCIAL_PROOF, f"Teams running paid acquisition in-house need repeatable creative systems, not one-off ideas."),
    ]
    return [
        Hook(type=hook_type, text=text, rationale=f"Product-grounded fallback hook for {product.lower()}.")
        for hook_type, text in templates[: payload.hook_count]
    ]


def _fallback_angles(payload: CreativeInput) -> list[MessagingAngle]:
    first_benefit = payload.key_benefits[0]
    angles = [
        MessagingAngle(
            name="Volume Without Headcount",
            description=f"Position {payload.brand_name} as the way to create more ads without adding a larger creative team.",
            target_emotion="relief",
            use_case="Best for founders and lean growth teams under output pressure.",
        ),
        MessagingAngle(
            name="Faster Launch Loop",
            description=f"Focus on how the product compresses the time between brief, concept, and live campaign using {first_benefit.lower()}.",
            target_emotion="momentum",
            use_case="Best when the buyer values speed to market.",
        ),
        MessagingAngle(
            name="Higher Quality Cold Traffic Creative",
            description="Frame the product as a quality control system that improves hooks, message-match, and creative specificity.",
            target_emotion="confidence",
            use_case="Best for performance marketers tired of generic AI outputs.",
        ),
    ]
    return angles[: payload.angle_count]


def _fallback_ad_copies(payload: CreativeInput, hooks: list[Hook], angles: list[MessagingAngle]) -> list[AdCopy]:
    limits = payload.copy_count
    copies: list[AdCopy] = []
    for index in range(limits):
        hook = hooks[index % len(hooks)]
        angle = angles[index % len(angles)]
        copies.append(
            AdCopy(
                hook_text=hook.text,
                angle_name=angle.name,
                primary_text=f"{payload.brand_name} helps {payload.target_audience.lower()} turn one product brief into hooks, copy, concepts, and final ad assets faster. {payload.key_benefits[0]}.",
                headline=f"{payload.brand_name} builds final ads faster",
                cta="Generate Ads",
                description=f"{angle.name} for {payload.platform.value} campaigns.",
            )
        )
    return copies


def _fallback_visual_concepts(
    payload: CreativeInput,
    hooks: list[Hook],
    angles: list[MessagingAngle],
) -> list[VisualConceptDraft]:
    aspect_ratio = "9:16" if payload.platform == Platform.TIKTOK else "1:1"
    concepts: list[VisualConceptDraft] = []
    for index in range(payload.concept_count):
        hook = hooks[index % len(hooks)]
        angle = angles[index % len(angles)]
        concepts.append(
            VisualConceptDraft(
                hook_text=hook.text,
                angle_name=angle.name,
                scene_description=(
                    f"Close-up of a laptop showing an ad workflow for {payload.brand_name}, with the product UI visible, "
                    f"a marketer reviewing creative outputs, and clear product presence tied to {payload.key_benefits[0].lower()}."
                ),
                camera_angle="three-quarter desk view",
                background_setting="modern workspace with warm daylight and subtle brand-colored accents",
                color_palette=(payload.brand_colors[:3] if payload.brand_colors else ["#111111", "#F4F1EA", "#E85D04"]),
                mood="confident, productive, conversion-focused",
                style_reference="clean commercial product ad photography",
                aspect_ratio=aspect_ratio,
                media_type=MediaType.IMAGE,
            )
        )
    return concepts
