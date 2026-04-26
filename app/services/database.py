import json
from app.core.config import Settings
from app.core.supabase import get_db_connection
from app.models import CampaignPackage


class CampaignDatabase:
    def __init__(self, settings: Settings) -> None:
        self._conn = get_db_connection(settings)

    def save_campaign(self, package: CampaignPackage) -> str | None:
        if not self._conn:
            return None
        try:
            with self._conn.cursor() as cur:
                query = """
                    INSERT INTO creative_campaigns (
                        campaign_name, campaign_slug, brand_name, platform, objective,
                        input_data, hooks, angles, ad_copies, visual_concepts,
                        generated_creatives, scored_creatives, creative_assets
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id;
                """
                
                # psycopg2 handles dicts/lists best if we wrap in json.dumps
                values = (
                    package.campaign_name,
                    package.campaign_slug,
                    package.input.brand_name,
                    package.input.platform.value,
                    package.input.objective.value,
                    json.dumps(package.input.model_dump(mode="json")),
                    json.dumps([h.model_dump(mode="json") for h in package.hooks]),
                    json.dumps([a.model_dump(mode="json") for a in package.angles]),
                    json.dumps([c.model_dump(mode="json") for c in package.ad_copies]),
                    json.dumps([v.model_dump(mode="json") for v in package.visual_concepts]),
                    json.dumps([g.model_dump(mode="json") for g in package.generated_creatives]),
                    json.dumps([s.model_dump(mode="json") for s in package.scored_creatives]),
                    json.dumps([a.model_dump(mode="json") for a in package.creative_assets]),
                )
                
                cur.execute(query, values)
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Database save error: {e}")
            return None

    def get_campaigns(self, limit: int = 20) -> list:
        if not self._conn:
            return []
        try:
            with self._conn.cursor() as cur:
                query = """
                    SELECT id, campaign_name, campaign_slug, brand_name, platform, objective, created_at
                    FROM creative_campaigns
                    ORDER BY created_at DESC
                    LIMIT %s;
                """
                cur.execute(query, (limit,))
                columns = [desc[0] for desc in cur.description]
                results = []
                for row in cur.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Handle datetime serialization if necessary
                    if 'created_at' in row_dict and row_dict['created_at']:
                        row_dict['created_at'] = row_dict['created_at'].isoformat()
                    results.append(row_dict)
                return results
        except Exception as e:
            print(f"Database fetch error: {e}")
            return []