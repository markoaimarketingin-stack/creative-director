from app.core.config import Settings
from app.core.supabase import get_supabase_client
from app.models import CampaignPackage


class CampaignDatabase:
    def __init__(self, settings: Settings) -> None:
        self._client = get_supabase_client(settings)

    def save_campaign(self, package: CampaignPackage) -> str | None:
        if not self._client:
            return None
        try:
            data = {
                "campaign_name": package.campaign_name,
                "campaign_slug": package.campaign_slug,
                "brand_name": package.input.brand_name,
                "platform": package.input.platform.value,
                "objective": package.input.objective.value,
                "input_data": package.input.model_dump(mode="json"),
                "hooks": [h.model_dump(mode="json") for h in package.hooks],
                "angles": [a.model_dump(mode="json") for a in package.angles],
                "ad_copies": [c.model_dump(mode="json") for c in package.ad_copies],
                "visual_concepts": [v.model_dump(mode="json") for v in package.visual_concepts],
                "generated_creatives": [g.model_dump(mode="json") for g in package.generated_creatives],
                "scored_creatives": [s.model_dump(mode="json") for s in package.scored_creatives],
                "creative_assets": [a.model_dump(mode="json") for a in package.creative_assets],
            }
            result = self._client.table("creative_campaigns").insert(data).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            print(f"Supabase save error: {e}")
            return None

    def get_campaigns(self, limit: int = 20) -> list:
        if not self._client:
            return []
        try:
            result = (
                self._client.table("creative_campaigns")
                .select("id, campaign_name, campaign_slug, brand_name, platform, objective, created_at")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            print(f"Supabase fetch error: {e}")
            return []