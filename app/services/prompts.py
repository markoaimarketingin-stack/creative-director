import json
from collections.abc import Iterable

from pydantic import BaseModel

from app.models import AdCopy, CreativeInput, Hook, MessagingAngle, Platform, VisualConcept, VisualConceptDraft

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
    "You are Creative Director Engine, a senior direct-response creative strategist and ad production planner. "
    "Return only valid JSON matching the requested schema. "
    "Every output must be specific to the product, use case, audience, and platform. "
    "Avoid cinematic fluff, generic startup language, empty hype, vague visuals, and unsupported claims. "
    "Think like a paid-media operator building ads that ship this week."
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
    required_types = ["curiosity", "fear_based", "benefit_driven", "contrarian", "social_proof"]
    return (
        "Task: Generate high-converting paid-media hooks.\n\n"
        f"{brand_context(payload)}\n\n"
        f"Return JSON with a top-level `hooks` array containing exactly {payload.hook_count} objects.\n"
        "Each object must contain: `type`, `text`, `rationale`.\n"
        f"Allowed `type` values only: {', '.join(required_types)}.\n"
        "Distribution rules:\n"
        "- Cover all five hook types at least once before repeating any type.\n"
        "- Vary mechanism, emotional trigger, and sentence structure.\n"
        "- Make the product and user outcome obvious in the hook itself.\n"
        "- No duplicate ideas with different wording.\n"
        "- No generic curiosity-only hooks.\n"
        "- No brand manifesto language.\n"
        "Write hooks as deployable ad openers, not brainstorm fragments."
    )


def angle_prompt(payload: CreativeInput) -> str:
    return (
        "Task: Generate platform-aware messaging angles for this campaign.\n\n"
        f"{brand_context(payload)}\n\n"
        f"Return JSON with a top-level `angles` array containing exactly {payload.angle_count} objects.\n"
        "Each object must contain: `name`, `description`, `target_emotion`, `use_case`.\n"
        "Angle rules:\n"
        "- Each angle must be materially different in sales argument, not just tone.\n"
        "- Anchor each angle in a concrete buyer problem, desired outcome, or proof mechanism.\n"
        "- Prefer direct-response utility over abstract storytelling.\n"
        "- Avoid repeating the same benefit in five ways."
    )


def ad_copy_prompt(payload: CreativeInput, hooks: list[Hook], angles: list[MessagingAngle]) -> str:
    return (
        "You are an expert performance marketing copywriter specializing in high-converting ads for Meta, Instagram, and Google.\n"
        "Your task is to generate ultra-concise, high-impact ad copy that maximizes scroll-stopping power and click-through rate (CTR).\n\n"
        f"{brand_context(payload)}\n\n"
        "Use these hooks:\n"
        f"{serialize_selected(hooks[: min(len(hooks), payload.copy_count)], ['type', 'text'])}\n\n"
        "Use these messaging angles:\n"
        f"{serialize_selected(angles, ['name', 'description', 'target_emotion'])}\n\n"
        f"Return JSON with a top-level `ad_copies` array containing exactly {payload.copy_count} objects.\n"
        "STRICT RULES (MUST FOLLOW):\n\n"
        "1. PRIMARY TEXT:\n"
        "- Max 12 words\n"
        "- Only ONE sentence\n"
        "- Must be either: (a) A punchy emotional statement OR (b) A curiosity-driven hook\n"
        "- Do NOT explain the product or use filler words\n"
        "- Must feel premium, sharp, and instantly engaging\n\n"
        "2. HEADLINE:\n"
        "- Max 6 words\n"
        "- Focus on clear benefit, aspiration, or transformation\n"
        "- Strong, bold, and direct\n"
        "- No punctuation unless absolutely necessary\n\n"
        "3. DESCRIPTION:\n"
        "- Max 5 words, minimum 5 characters (or return empty string)\n"
        "- Add ONLY if it strengthens clarity or urgency, otherwise return an empty string\n"
        "- Must be complete phrase if provided (not abbreviations or single words)\n\n"
        "4. VARIATIONS & STYLE:\n"
        "- Rotate between these 3 styles: Emotional Hook, Curiosity Hook, Minimalist Premium\n"
        "- Avoid generic phrases like 'high quality', 'best product', 'crafted for you'\n"
        "- Prefer emotional triggers: confidence, status, transformation, desire, curiosity\n\n"
        "OUTPUT FORMAT (STRICT JSON):\n"
        "Each object must include: `hook_text`, `angle_name`, `primary_text`, `headline`, `cta`, and `description`."
    )


def visual_concept_prompt(
    payload: CreativeInput,
    hooks: list[Hook],
    angles: list[MessagingAngle],
    ad_copies: list[AdCopy] | None = None,
) -> str:
    aspect_ratios = ", ".join(PLATFORM_ASPECT_RATIOS[payload.platform])
    copy_context = ""
    if ad_copies:
        copy_context = (
            "Candidate hook-angle-copy combinations. Select the strongest combinations for the visuals, "
            "prioritizing clear buyer desire, product relevance, and CTA alignment:\n"
            f"{serialize_selected(ad_copies[: min(len(ad_copies), payload.concept_count * 2)], ['hook_text', 'angle_name', 'primary_text', 'headline', 'cta', 'description'])}\n\n"
        )
    return (
        "Task: Generate visual ad concepts that can be handed to an image generation model.\n\n"
        f"{brand_context(payload)}\n\n"
        "Reference hooks:\n"
        f"{serialize_selected(hooks[: min(len(hooks), payload.concept_count)], ['text'])}\n\n"
        "Reference angles:\n"
        f"{serialize_selected(angles, ['name', 'description'])}\n\n"
        f"{copy_context}"
        f"Return JSON with a top-level `visual_concepts` array containing exactly {payload.concept_count} objects.\n"
        f"Prefer these aspect ratios for {payload.platform.value}: {aspect_ratios}.\n"
        "Each concept must contain: `hook_text`, `angle_name`, `scene_description`, `camera_angle`, "
        "`background_setting`, `color_palette`, `mood`, `style_reference`, `aspect_ratio`, `media_type`.\n"
        "Visual rules:\n"
        "- Choose the best hook and angle pair from the supplied combinations. The chosen hook_text and angle_name must exactly match one supplied combination when possible.\n"
        "- The product must be visible, central, and physically believable in the scene.\n"
        "- Favor product-in-use, packaging, hands, environment, or demonstrable outcome over cinematic metaphor.\n"
        "- Include concrete shot direction, not vague art direction.\n"
        "- Design the image as a finished ad layout with visual, headline area, short bodyline area, and CTA button already integrated.\n"
        "- Avoid surreal collage, floating objects, luxury editorial clichés, and generic neon backgrounds."
    )


def nanobanana_prompt(
    payload: CreativeInput,
    concept: VisualConceptDraft | VisualConcept,
    ad_copy: AdCopy | None = None,
) -> str:
    benefit_line = ", ".join(payload.key_benefits[:3])
    copy_direction = ""
    if ad_copy:
        copy_direction = (
            f"Selected hook: {ad_copy.hook_text}. Selected angle: {ad_copy.angle_name}. "
            "The final image must already contain these exact readable text elements as part of the design: "
            f"headline text \"{ad_copy.headline}\"; bodyline text \"{ad_copy.primary_text}\"; "
            f"CTA button text \"{ad_copy.cta}\". "
            "Use clean commercial typography, strong contrast, correct spelling, and a clear CTA button. "
        )
    return (
        f"Create a {concept.aspect_ratio} {concept.media_type.value} performance ad creative for {payload.brand_name}. "
        f"Scene: {concept.scene_description}. Camera angle: {concept.camera_angle}. "
        f"Background: {concept.background_setting}. Mood: {concept.mood}. "
        f"Style: {concept.style_reference}. Palette: {', '.join(concept.color_palette)}. "
        f"Audience: {payload.target_audience}. Objective: {payload.objective.value}. "
        f"{copy_direction}"
        f"Core benefit cues: {benefit_line}. Platform-native look for {payload.platform.value}. "
        "Keep the product large, readable, and grounded in realistic usage. "
        "Commercially realistic, product-led, high-contrast, no watermarks, no floating UI, no abstract movie-poster composition. "
        "Generate the complete finished ad image with the visual, headline, bodyline, and CTA button already present in the image."
    )


def huggingface_prompt(
    payload: CreativeInput,
    concept: VisualConceptDraft | VisualConcept,
    ad_copy: AdCopy | None = None,
) -> str:
    """Generate prompt for Stable Diffusion v1.5 to render ads WITH TEXT INTEGRATED."""
    benefit_line = ", ".join(payload.key_benefits[:3])
    copy_direction = ""
    if ad_copy:
        copy_direction = (
            f"TEXT IN IMAGE - Must render these exactly as written: "
            f"TOP TEXT: {ad_copy.headline} | "
            f"MIDDLE TEXT: {ad_copy.primary_text} | "
            f"BOTTOM TEXT/CTA: {ad_copy.cta}. "
            "White text with dark background or black text with light background. Bold, readable. "
        )
    return (
        f"Professional ad for {payload.brand_name}. Size {concept.aspect_ratio}. "
        f"{copy_direction}"
        f"Scene: {concept.scene_description}. "
        f"View: {concept.camera_angle}. "
        f"Background: {concept.background_setting}. "
        f"Lighting: {concept.mood}. "
        f"Style: {concept.style_reference}. "
        f"Colors: {', '.join(concept.color_palette)}. "
        f"For: {payload.target_audience}. "
        f"Goal: {payload.objective.value}. "
        f"Message: {benefit_line}. "
        f"Where: {payload.platform.value}. "
        "Product big and clear, real usage shown, professional ad look. "
        "Text must be in image, readable, correct spelling."
    )


def scoring_prompt(
    payload: CreativeInput,
    concept: VisualConcept,
    copy: dict[str, str],
) -> str:
    return (
        "Task: Evaluate one finished ad concept for direct-response quality.\n\n"
        f"{brand_context(payload)}\n\n"
        f"Visual concept: {json.dumps(concept.model_dump(mode='json'), separators=(',', ':'))}\n"
        f"Copy payload: {json.dumps(copy, separators=(',', ':'))}\n\n"
        "Return only JSON with keys: `clarity`, `persuasion`, `cta_alignment`, `platform_fit`, `rationale`.\n"
        "Scoring rubric:\n"
        "- clarity: Is the message instantly understandable?\n"
        "- persuasion: Does it create desire, urgency, or credibility?\n"
        "- cta_alignment: Does the CTA match the promise and objective?\n"
        "- platform_fit: Does it feel native to the platform and constraints?\n"
        "Use 0-100 integers. Be strict. Penalize generic copy, mismatched CTA, unclear value prop, or abstract visuals."
    )
