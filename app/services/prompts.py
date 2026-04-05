import json
from collections.abc import Iterable

from pydantic import BaseModel

from app.models import CreativeInput, Hook, MessagingAngle, Platform, VisualConcept, VisualConceptDraft

PLATFORM_COPY_LIMITS: dict[Platform, dict[str, int]] = {
    Platform.META: {"primary_text": 125, "headline": 40, "description": 30},
    Platform.GOOGLE: {"primary_text": 90, "headline": 30, "description": 90},
    Platform.TIKTOK: {"primary_text": 100, "headline": 40, "description": 80},
}

PLATFORM_ASPECT_RATIOS: dict[Platform, list[str]] = {
    Platform.META: ["1:1", "4:5", "9:16"],
    Platform.GOOGLE: ["1:1", "16:9", "1.91:1"],
    Platform.TIKTOK: ["9:16"],
}

CREATIVE_SYSTEM_PROMPT = (
    "You are Creative Director Engine, a senior direct-response creative strategist. "
    "Produce sharp, commercially useful ad outputs with concrete emotional hooks, "
    "distinct messaging angles, and platform-specific execution. Keep outputs original, "
    "specific, and conversion-focused. Return only the requested schema."
)


def brand_context(payload: CreativeInput) -> str:
    return (
        f"Brand: {payload.brand_name}\n"
        f"Product: {payload.product_description}\n"
        f"Audience: {payload.target_audience}\n"
        f"Platform: {payload.platform.value}\n"
        f"Objective: {payload.objective.value}\n"
        f"Tone: {payload.tone}\n"
        f"Key benefits: {', '.join(payload.key_benefits)}\n"
        f"Competitors: {', '.join(payload.competitors) if payload.competitors else 'None listed'}\n"
        f"Visual style: {payload.visual_style or 'Not specified'}"
    )


def serialize_models(items: Iterable[object]) -> str:
    serialized_items = [
        item.model_dump(mode="json") if isinstance(item, BaseModel) else item
        for item in items
    ]
    return json.dumps(
        serialized_items,
        separators=(",", ":"),
    )


def serialize_selected(items: Iterable[BaseModel], fields: list[str]) -> str:
    selected = [{field: getattr(item, field) for field in fields} for item in items]
    return json.dumps(selected, separators=(",", ":"))


def hook_prompt(payload: CreativeInput) -> str:
    return (
        "Generate high-converting ad hooks.\n\n"
        f"{brand_context(payload)}\n\n"
        f"Create exactly {payload.hook_count} hooks.\n"
        "Requirements:\n"
        "- Cover curiosity, fear-based, benefit-driven, contrarian, and social-proof hook types.\n"
        "- At least two hooks per type.\n"
        "- Use emotional triggers, curiosity gaps, and direct-response principles.\n"
        "- Avoid vague claims and generic startup buzzwords.\n"
        "- Make each hook feel ready for paid media, not brand poetry.\n"
        "- Write one short rationale per hook."
    )


def angle_prompt(payload: CreativeInput) -> str:
    return (
        "Generate platform-aware messaging angles for this campaign.\n\n"
        f"{brand_context(payload)}\n\n"
        f"Create exactly {payload.angle_count} distinct messaging angles.\n"
        "Angles should span problem-solution, before-after, aspirational identity, authority, "
        "and emotional storytelling where relevant. Each angle needs a name, description, "
        "target emotion, and best use case."
    )


def ad_copy_prompt(payload: CreativeInput, hooks: list[Hook], angles: list[MessagingAngle]) -> str:
    limits = PLATFORM_COPY_LIMITS[payload.platform]
    return (
        "Generate paid social or paid search ad copy variations.\n\n"
        f"{brand_context(payload)}\n\n"
        f"Platform character targets: primary_text <= {limits['primary_text']}, "
        f"headline <= {limits['headline']}, description <= {limits['description']}.\n\n"
        "Use these hooks:\n"
        f"{serialize_selected(hooks[: min(len(hooks), payload.copy_count)], ['type', 'text'])}\n\n"
        "Use these messaging angles:\n"
        f"{serialize_selected(angles, ['name', 'description', 'target_emotion'])}\n\n"
        f"Create exactly {payload.copy_count} ad copy variants.\n"
        "Every variant must include hook_text, angle_name, primary_text, headline, CTA, and description.\n"
        "Keep copy tight, scannable, and native to the selected platform."
    )


def visual_concept_prompt(payload: CreativeInput, hooks: list[Hook], angles: list[MessagingAngle]) -> str:
    aspect_ratios = ", ".join(PLATFORM_ASPECT_RATIOS[payload.platform])
    return (
        "Generate visual ad concepts that can be handed to an image generation model.\n\n"
        f"{brand_context(payload)}\n\n"
        "Reference hooks:\n"
        f"{serialize_selected(hooks[: min(len(hooks), payload.concept_count)], ['text'])}\n\n"
        "Reference angles:\n"
        f"{serialize_selected(angles, ['name', 'description'])}\n\n"
        f"Create exactly {payload.concept_count} concepts.\n"
        f"Prefer these aspect ratios for {payload.platform.value}: {aspect_ratios}.\n"
        "Each concept needs: hook_text, angle_name, scene_description, camera_angle, "
        "background_setting, color_palette, mood, style_reference, aspect_ratio, media_type.\n"
        "Favor concrete scenes over abstract collage language."
    )


def nanobanana_prompt(payload: CreativeInput, concept: VisualConceptDraft | VisualConcept) -> str:
    benefit_line = ", ".join(payload.key_benefits[:3])
    return (
        f"Create a {concept.aspect_ratio} {concept.media_type.value} performance ad creative for {payload.brand_name}. "
        f"Scene: {concept.scene_description}. Camera angle: {concept.camera_angle}. "
        f"Background: {concept.background_setting}. Mood: {concept.mood}. "
        f"Style: {concept.style_reference}. Palette: {', '.join(concept.color_palette)}. "
        f"Audience: {payload.target_audience}. Objective: {payload.objective.value}. "
        f"Core benefit cues: {benefit_line}. Platform-native look for {payload.platform.value}. "
        "Product-led, polished, high-contrast, scroll-stopping, commercially realistic, no watermarks."
    )
