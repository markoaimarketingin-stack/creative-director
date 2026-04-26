import json
from app.core.config import Settings
from app.core.supabase import get_db_connection
from app.models import CampaignPackage


class ChatDatabase:
    def __init__(self, settings: Settings) -> None:
        self._conn = get_db_connection(settings)
        self._init_db()

    def _init_db(self):
        if not self._conn:
            return
        try:
            with self._conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
                """)
        except Exception as e:
            print(f"Chat DB Init Error: {e}")

    def save_message(self, session_id: str, role: str, content: str):
        if not self._conn:
            return
        import uuid
        msg_id = str(uuid.uuid4())
        try:
            with self._conn.cursor() as cur:
                # Ensure the session exists in chat_sessions table to satisfy foreign key
                cur.execute("SELECT id FROM chat_sessions WHERE id = %s", (session_id,))
                if not cur.fetchone():
                    title = content[:30] + ("..." if len(content) > 30 else "") if role == "user" else "Creative Assistant Chat"
                    cur.execute("""
                        INSERT INTO chat_sessions (id, title)
                        VALUES (%s, %s);
                    """, (session_id, title))

                cur.execute("""
                    INSERT INTO chat_messages (id, session_id, role, content)
                    VALUES (%s, %s, %s, %s);
                """, (msg_id, session_id, role, content))
        except Exception as e:
            print(f"Chat DB save error: {e}")

    def get_history(self, session_id: str) -> list[dict]:
        if not self._conn:
            return []
        try:
            with self._conn.cursor() as cur:
                cur.execute("""
                    SELECT role, content FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at ASC;
                """, (session_id,))
                return [{"role": row[0], "content": row[1]} for row in cur.fetchall()]
        except Exception as e:
            print(f"Chat DB get error: {e}")
            return []

    def get_sessions(self) -> list[dict]:
        if not self._conn:
            return []
        try:
            with self._conn.cursor() as cur:
                cur.execute("""
                    SELECT m.session_id, max(m.created_at) as last_activity, s.title
                    FROM chat_messages m
                    LEFT JOIN chat_sessions s ON m.session_id = s.id
                    GROUP BY m.session_id, s.title
                    ORDER BY last_activity DESC
                    LIMIT 20;
                """)
                return [{"session_id": row[0], "last_activity": row[1].isoformat(), "title": row[2]} for row in cur.fetchall()]
        except Exception as e:
            print(f"Chat DB get sessions error: {e}")
            return []
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