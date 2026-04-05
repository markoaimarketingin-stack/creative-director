from typing import Any

from app.models import AdCopy, AdCopySet, Hook, HookSet, HookType, MediaType, MessagingAngle, MessagingAngleSet, VisualConceptDraft, VisualConceptSet


def normalize_hook_set(payload: dict[str, Any]) -> HookSet:
    items = _extract_items(payload, primary_keys=("hooks", "items"))
    hooks: list[Hook] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        hook_type = _normalize_hook_type(item.get("type"))
        text = _as_text(item.get("text") or item.get("hook") or item.get("headline"))
        rationale = _as_text(item.get("rationale") or item.get("reason") or item.get("description"))
        if not text:
            continue
        hooks.append(
            Hook(
                type=hook_type,
                text=text,
                rationale=rationale or "Built as a direct-response hook for paid acquisition testing.",
            )
        )
    if not hooks:
        raise RuntimeError("Groq returned no usable hooks.")
    return HookSet(hooks=hooks)


def normalize_angle_set(payload: dict[str, Any]) -> MessagingAngleSet:
    items = _extract_items(payload, primary_keys=("angles", "messaging_angles", "items"))
    angles: list[MessagingAngle] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _as_text(item.get("name") or item.get("title") or item.get("angle_name"))
        description = _as_text(item.get("description") or item.get("summary"))
        target_emotion = _as_text(item.get("target_emotion") or item.get("emotion")) or "confidence"
        use_case = _as_text(item.get("use_case") or item.get("best_use_case") or item.get("best_for")) or "Paid acquisition campaigns"
        if not name or not description:
            continue
        angles.append(
            MessagingAngle(
                name=name,
                description=description,
                target_emotion=target_emotion,
                use_case=use_case,
            )
        )
    if not angles:
        raise RuntimeError("Groq returned no usable messaging angles.")
    return MessagingAngleSet(angles=angles)


def normalize_ad_copy_set(payload: dict[str, Any]) -> AdCopySet:
    items = _extract_items(payload, primary_keys=("ad_copies", "variants", "copies", "items"))
    ad_copies: list[AdCopy] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        hook_text = _as_text(item.get("hook_text") or item.get("hook") or item.get("anchor"))
        angle_name = _as_text(item.get("angle_name") or item.get("angle") or item.get("name"))
        primary_text = _as_text(item.get("primary_text") or item.get("body") or item.get("copy"))
        headline = _as_text(item.get("headline") or item.get("title"))
        cta = _as_text(item.get("cta") or item.get("CTA") or item.get("cta_text")) or "Learn more"
        description = _as_text(item.get("description") or item.get("supporting_text")) or "Performance-focused creative variant."
        if not hook_text or not angle_name or not primary_text or not headline:
            continue
        ad_copies.append(
            AdCopy(
                hook_text=hook_text,
                angle_name=angle_name,
                primary_text=primary_text,
                headline=headline,
                cta=cta,
                description=description,
            )
        )
    if not ad_copies:
        raise RuntimeError("Groq returned no usable ad copy variants.")
    return AdCopySet(ad_copies=ad_copies)


def normalize_visual_concept_set(payload: dict[str, Any]) -> VisualConceptSet:
    items = _extract_items(payload, primary_keys=("visual_concepts", "concepts", "items"))
    concepts: list[VisualConceptDraft] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        hook_text = _as_text(item.get("hook_text") or item.get("hook") or item.get("headline"))
        angle_name = _as_text(item.get("angle_name") or item.get("angle") or item.get("name"))
        scene_description = _as_text(item.get("scene_description") or item.get("scene") or item.get("description"))
        if not hook_text or not angle_name or not scene_description:
            continue
        concepts.append(
            VisualConceptDraft(
                hook_text=hook_text,
                angle_name=angle_name,
                scene_description=scene_description,
                camera_angle=_as_text(item.get("camera_angle")) or "eye-level product shot",
                background_setting=_as_text(item.get("background_setting")) or "clean modern campaign backdrop",
                color_palette=_normalize_palette(item.get("color_palette")),
                mood=_as_text(item.get("mood")) or "high-conviction",
                style_reference=_as_text(item.get("style_reference") or item.get("style")) or "performance marketing still",
                aspect_ratio=_as_text(item.get("aspect_ratio")) or "1:1",
                media_type=_normalize_media_type(item.get("media_type")),
            )
        )
    if not concepts:
        raise RuntimeError("Groq returned no usable visual concepts.")
    return VisualConceptSet(visual_concepts=concepts)


def _extract_items(payload: dict[str, Any], *, primary_keys: tuple[str, ...]) -> list[Any]:
    for key in primary_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.values())

    concept_like = [value for key, value in payload.items() if key.lower().replace(" ", "").startswith("concept") and isinstance(value, dict)]
    if concept_like:
        return concept_like

    if all(isinstance(value, dict) for value in payload.values()) and payload:
        return list(payload.values())

    return []


def _normalize_hook_type(value: Any) -> HookType:
    token = _as_text(value).lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "curiosity": HookType.CURIOSITY,
        "fear_based": HookType.FEAR_BASED,
        "benefit_driven": HookType.BENEFIT_DRIVEN,
        "contrarian": HookType.CONTRARIAN,
        "social_proof": HookType.SOCIAL_PROOF,
    }
    return mapping.get(token, HookType.CURIOSITY)


def _normalize_media_type(value: Any) -> MediaType:
    token = _as_text(value).lower().replace("-", "_").replace(" ", "_")
    return MediaType.VIDEO if token == "video" else MediaType.IMAGE


def _normalize_palette(value: Any) -> list[str]:
    if isinstance(value, list):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        tokens = [item.strip() for item in value.split(",") if item.strip()]
    else:
        tokens = []

    if len(tokens) < 2:
        tokens.extend(["#1f2937", "#f59e0b"])
    return tokens[:5]


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())
