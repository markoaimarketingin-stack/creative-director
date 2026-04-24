from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"


class Objective(str, Enum):
    CONVERSIONS = "conversions"
    TRAFFIC = "traffic"
    AWARENESS = "awareness"


class HookType(str, Enum):
    CURIOSITY = "curiosity"
    FEAR_BASED = "fear_based"
    BENEFIT_DRIVEN = "benefit_driven"
    CONTRARIAN = "contrarian"
    SOCIAL_PROOF = "social_proof"


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class CreativeStatus(str, Enum):
    GENERATED = "generated"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


class CreativeInput(BaseModel):
    brand_name: str = Field(..., min_length=2)
    product_description: str = Field(..., min_length=10)
    target_audience: str = Field(..., min_length=3)
    platform: Platform
    objective: Objective
    tone: str = Field(..., min_length=2)
    key_benefits: list[str] = Field(..., min_length=1)
    competitors: list[str] = Field(default_factory=list)
    visual_style: str | None = None
    sample_images: list[str] = Field(default_factory=list)

    campaign_name: str | None = None
    hook_count: int = Field(default=15, ge=10, le=20)
    angle_count: int = Field(default=5, ge=3, le=7)
    copy_count: int = Field(default=20, ge=5, le=30)
    concept_count: int = Field(default=5, ge=1, le=10)

    @field_validator("brand_name", "product_description", "target_audience", "tone", "visual_style")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split())

    @field_validator("key_benefits", "competitors")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        return [" ".join(item.split()) for item in values if item and item.strip()]


class Hook(BaseModel):
    type: HookType
    text: str = Field(..., min_length=5)
    rationale: str = Field(..., min_length=10)


class HookSet(BaseModel):
    hooks: list[Hook] = Field(..., min_length=1)


class MessagingAngle(BaseModel):
    name: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    target_emotion: str = Field(..., min_length=3)
    use_case: str = Field(..., min_length=5)


class MessagingAngleSet(BaseModel):
    angles: list[MessagingAngle] = Field(..., min_length=1)


class AdCopy(BaseModel):
    copy_id: str | None = None
    hook_text: str = Field(..., min_length=5)
    angle_name: str = Field(..., min_length=3)
    primary_text: str = Field(..., min_length=10)
    headline: str = Field(..., min_length=3)
    cta: str = Field(..., min_length=2)
    description: str = Field(..., min_length=5)
    total_score: int | None = Field(default=None, ge=0, le=100)
    score_rank: int | None = Field(default=None, ge=1)
    score_rationale: str | None = None


class AdCopySet(BaseModel):
    ad_copies: list[AdCopy] = Field(..., min_length=1)


class VisualConceptDraft(BaseModel):
    hook_text: str = Field(..., min_length=5)
    angle_name: str = Field(..., min_length=3)
    scene_description: str = Field(..., min_length=10)
    camera_angle: str = Field(..., min_length=3)
    background_setting: str = Field(..., min_length=5)
    color_palette: list[str] = Field(..., min_length=2)
    mood: str = Field(..., min_length=3)
    style_reference: str = Field(..., min_length=3)
    aspect_ratio: str = Field(..., min_length=3)
    media_type: MediaType = MediaType.IMAGE


class VisualConceptSet(BaseModel):
    visual_concepts: list[VisualConceptDraft] = Field(..., min_length=1)


class VisualConcept(VisualConceptDraft):
    concept_id: str
    generation_prompt: str = Field(..., min_length=15)


class GeneratedCreative(BaseModel):
    concept_id: str
    provider: str
    provider_api_version: str | None = None
    status: CreativeStatus
    prompt: str
    image_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class CreativeScore(BaseModel):
    concept_id: str
    emotional_intensity: int = Field(..., ge=0, le=100)
    clarity: int = Field(..., ge=0, le=100)
    uniqueness: int = Field(..., ge=0, le=100)
    platform_fit: int = Field(..., ge=0, le=100)
    total_score: int = Field(..., ge=0, le=100)
    rank: int | None = None
    rationale: str = Field(..., min_length=10)


class CreativeAsset(BaseModel):
    campaign_name: str
    campaign_slug: str
    platform: Platform
    objective: Objective
    concept_id: str
    hook_type: HookType | None = None
    hook_text: str
    angle_name: str
    target_emotion: str | None = None
    primary_text: str | None = None
    headline: str | None = None
    description: str | None = None
    cta: str | None = None
    visual_concept: VisualConcept
    generated_creative: GeneratedCreative
    score: CreativeScore


class CampaignPackage(BaseModel):
    campaign_name: str
    campaign_slug: str
    created_at: datetime
    input: CreativeInput
    hooks: list[Hook]
    angles: list[MessagingAngle]
    ad_copies: list[AdCopy]
    visual_concepts: list[VisualConcept]
    generated_creatives: list[GeneratedCreative]
    scored_creatives: list[CreativeScore]
    creative_assets: list[CreativeAsset]
    output_directory: str | None = None


class TopCreativeItem(BaseModel):
    campaign_name: str
    campaign_slug: str
    platform: Platform
    concept_id: str
    total_score: int
    headline: str | None = None
    cta: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    output_directory: str


class TopCreativesResponse(BaseModel):
    items: list[TopCreativeItem]
