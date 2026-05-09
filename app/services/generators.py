import re
from collections import OrderedDict, defaultdict

from app.models import (
    AdCopy,
    CreativeInput,
    Hook,
    HookType,
    MediaType,
    MessagingAngle,
    Objective,
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
    huggingface_prompt,
    nanobanana_prompt,
    premium_nanobanana_prompt,
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
        except Exception as exc:
            print(f"[WARN] HookGenerator fallback in use: {type(exc).__name__}: {exc}")
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
        except Exception as exc:
            print(f"[WARN] MessagingAngleGenerator fallback in use: {type(exc).__name__}: {exc}")
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
        except Exception as exc:
            print(f"[WARN] AdCopyGenerator fallback in use: {type(exc).__name__}: {exc}")
            result = type("CopyResult", (), {"ad_copies": _fallback_ad_copies(payload, hooks, angles)})()

        limits = PLATFORM_COPY_LIMITS[payload.platform]
        normalized: list[AdCopy] = []
        for index, item in enumerate(result.ad_copies, start=1):
            polished = _polish_ad_copy(payload, item, index=index)
            normalized.append(
                AdCopy(
                    copy_id=f"copy-{index:02d}",
                    hook_text=polished.hook_text,
                    angle_name=polished.angle_name,
                    primary_text=smart_truncate(polished.primary_text, limits["primary_text"]),
                    headline=smart_truncate(polished.headline, limits["headline"]),
                    cta=smart_truncate(polished.cta, 24),
                    description=smart_truncate(polished.description, limits["description"], min_length=5),
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
        ad_copies: list[AdCopy] | None = None,
    ) -> list[VisualConcept]:
        try:
            raw_result = await self._llm.json_completion(
                instructions=CREATIVE_SYSTEM_PROMPT,
                user_prompt=visual_concept_prompt(payload, hooks, angles, ad_copies),
            )
            result = normalize_visual_concept_set(raw_result)
        except Exception as exc:
            print(f"[WARN] VisualConceptGenerator fallback in use: {type(exc).__name__}: {exc}")
            result = type("ConceptResult", (), {"visual_concepts": _fallback_visual_concepts(payload, hooks, angles)})()

        concepts: list[VisualConcept] = []
        for index, item in enumerate(result.visual_concepts[: payload.concept_count], start=1):
            draft = _normalize_visual_concept(item, platform=payload.platform)
            selected_copy = _match_ad_copy(draft, ad_copies or [])
            concepts.append(
                VisualConcept(
                    concept_id=f"concept-{index:02d}",
                    hook_text=selected_copy.hook_text if selected_copy else draft.hook_text,
                    angle_name=selected_copy.angle_name if selected_copy else draft.angle_name,
                    scene_description=draft.scene_description,
                    camera_angle=draft.camera_angle,
                    background_setting=draft.background_setting,
                    color_palette=draft.color_palette,
                    mood=draft.mood,
                    style_reference=draft.style_reference,
                    aspect_ratio=draft.aspect_ratio,
                    media_type=draft.media_type,
                    generation_prompt=premium_nanobanana_prompt(payload, draft, selected_copy),
                )
            )
        return concepts


def _match_ad_copy(draft: VisualConceptDraft, ad_copies: list[AdCopy]) -> AdCopy | None:
    for copy in ad_copies:
        if copy.hook_text == draft.hook_text and copy.angle_name == draft.angle_name:
            return copy
    for copy in ad_copies:
        if copy.angle_name == draft.angle_name:
            return copy
    for copy in ad_copies:
        if copy.hook_text == draft.hook_text:
            return copy
    return ad_copies[0] if ad_copies else None


def _normalize_visual_concept(draft: VisualConceptDraft, *, platform: Platform) -> VisualConceptDraft:
    if platform in {Platform.META, Platform.TIKTOK}:
        aspect_ratio = "9:16"
    else:
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


def smart_truncate(value: str, limit: int, min_length: int = 5) -> str:
    """
    Truncate text to fit within limit, but maintain at least min_length characters.
    
    Args:
        value: Text to truncate
        limit: Maximum character limit
        min_length: Minimum characters to preserve (default 5 for validation compatibility)
    """
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
        # Ensure we have at least min_length characters
        truncated = compact[:limit].rstrip()
        if len(truncated) < min_length:
            # If truncation would violate min_length, return first words instead
            for word in words:
                if len(word) <= min_length:
                    return word
            return truncated
        return truncated
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
    benefit = _value_phrase(payload)
    brand = payload.brand_name
    audience = _audience_phrase(payload.target_audience)
    templates = [
        (HookType.CURIOSITY, f"Why are {audience} switching to {brand} before launching new campaigns?"),
        (HookType.FEAR_BASED, f"Still shipping one ad angle at a time? That slows down testing and wastes spend."),
        (HookType.BENEFIT_DRIVEN, f"Build more launch-ready ads in less time with {benefit.lower()}."),
        (HookType.CONTRARIAN, f"The winning creative workflow is not more prompts. It is faster production with better outputs."),
        (HookType.SOCIAL_PROOF, f"Lean growth teams use tools like {brand} when they need more creative volume without adding headcount."),
        (HookType.CURIOSITY, f"What changes when one brief becomes hooks, copy, concepts, and final ads in one run?"),
        (HookType.FEAR_BASED, f"Generic hooks make cold traffic scroll past before your value prop lands."),
        (HookType.BENEFIT_DRIVEN, f"{benefit} across hooks, copy, concepts, and review-ready assets."),
        (HookType.CONTRARIAN, f"Pretty idea boards do not scale performance. Finished ads do."),
        (HookType.SOCIAL_PROOF, f"Teams buying traffic need repeatable creative systems, not one-off brainstorming."),
    ]
    return [
        Hook(type=hook_type, text=text, rationale="Fallback hook shaped for paid acquisition testing.")
        for hook_type, text in templates[: payload.hook_count]
    ]


def _fallback_angles(payload: CreativeInput) -> list[MessagingAngle]:
    first_benefit = _value_phrase(payload)
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
    primary_benefit = _value_phrase(payload)
    benefit_snippet = smart_truncate(primary_benefit.rstrip(".") + ".", 48)
    cta = _default_cta(payload)
    audience = _audience_phrase(payload.target_audience)
    for index in range(limits):
        hook = hooks[index % len(hooks)]
        angle = angles[index % len(angles)]
        headline = _fallback_headline(payload, angle.name, index=index)
        description = _fallback_description(payload, angle.name)
        copies.append(
            AdCopy(
                hook_text=hook.text,
                angle_name=angle.name,
                primary_text=(
                    f"For {audience.lower()}, {payload.brand_name} turns one brief into launch-ready ads faster. "
                    f"{benefit_snippet}"
                ),
                headline=headline,
                cta=cta,
                description=description,
            )
        )
    return copies


def _fallback_visual_concepts(
    payload: CreativeInput,
    hooks: list[Hook],
    angles: list[MessagingAngle],
) -> list[VisualConceptDraft]:
    aspect_ratio = "9:16" if payload.platform in {Platform.TIKTOK, Platform.META} else "1:1"
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


def _polish_ad_copy(payload: CreativeInput, item: AdCopy, *, index: int) -> AdCopy:
    headline = " ".join(item.headline.split())
    primary_text = " ".join(item.primary_text.split())
    description = " ".join(item.description.split())
    cta = " ".join(item.cta.split())

    audience = _audience_phrase(payload.target_audience)
    value_phrase = _value_phrase(payload)

    generic_headlines = {
        f"{payload.brand_name} builds final ads faster".lower(),
        f"{payload.brand_name} creates ads faster".lower(),
    }
    if not headline or headline.lower() in generic_headlines:
        headline = _fallback_headline(payload, item.angle_name, index=index)
    headline = _normalize_headline_completion(headline)

    if cta.lower() in {"generate ads", "generate", "click here", "learn", "buy"}:
        cta = _default_cta(payload)
    cta = _normalize_cta(cta, payload)

    if payload.brand_name.lower() not in primary_text.lower():
        primary_text = f"{payload.brand_name}: {primary_text}".strip(": ")

    # Removed minimum length filler logic to respect minimalist ad copy requirements.
    return AdCopy(
        hook_text=item.hook_text,
        angle_name=item.angle_name,
        primary_text=primary_text,
        headline=headline,
        cta=cta,
        description=description,
    )


def _normalize_headline_completion(headline: str) -> str:
    normalized = " ".join(headline.split()).strip()
    if not normalized:
        return normalized
    # Fix dangling time-number headlines like "Food In 10" -> "Food In 10 Minutes".
    if re.search(r"\b(?:in|within|under)\s+\d{1,3}$", normalized, flags=re.IGNORECASE):
        return f"{normalized} Minutes"
    return normalized


def _normalize_cta(cta: str, payload: CreativeInput) -> str:
    normalized = " ".join(cta.split()).strip()
    if not normalized:
        return _default_cta(payload)
    words = normalized.split()
    if len(words) == 1:
        return _default_cta(payload)
    if len(words) > 4:
        return " ".join(words[:4])
    return normalized


def _fallback_headline(payload: CreativeInput, angle_name: str, *, index: int) -> str:
    headlines = [
        f"Launch more ads with {payload.brand_name}",
        f"{payload.brand_name} speeds up creative production",
        f"From brief to ad set, faster",
        f"More creative output, less bottleneck",
        f"Build campaign-ready ads in less time",
    ]
    if "quality" in angle_name.lower():
        return f"Sharper ads for cold traffic"
    return headlines[index % len(headlines)]


def _fallback_description(payload: CreativeInput, angle_name: str) -> str:
    primary_benefit = _value_phrase(payload).rstrip(".")
    return f"{angle_name} built for {payload.platform.value} campaigns focused on {primary_benefit.lower()}."


def _default_cta(payload: CreativeInput) -> str:
    if payload.objective == Objective.CONVERSIONS:
        return "Get Started"
    if payload.objective == Objective.TRAFFIC:
        return "Learn More"
    return "See How It Works"


def _audience_phrase(audience: str) -> str:
    normalized = " ".join(audience.split())
    if not normalized:
        return "growth teams"
    stripped = normalized.replace(" ", "")
    if all(char.isdigit() or char in "-+" for char in stripped):
        return "growth teams"
    return normalized


def _value_phrase(payload: CreativeInput) -> str:
    preferred = next((item for item in payload.key_benefits if item and len(item.strip()) >= 5), "").strip()
    if preferred.lower() in {"cheap", "faster", "fast", "better", "affordable"}:
        preferred = ""
    if preferred:
        return preferred.rstrip(".")

    sentence = payload.product_description.split(".")[0].strip()
    if sentence:
        return sentence[0].upper() + sentence[1:]
    return "faster ad production"
