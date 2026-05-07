import json
import logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager

from app.core.config import Settings
from app.core.supabase import DatabasePool
from app.models import CampaignPackage

logger = logging.getLogger(__name__)


class BaseDatabase:
    def __init__(self, settings: Settings) -> None:
        self._pool = DatabasePool(settings)

    @contextmanager
    def _cursor(self) -> Generator:
        with self._pool.connection() as conn:
            if conn is None:
                yield None
                return
            with conn.cursor() as cur:
                yield cur

    def close(self) -> None:
        self._pool.close()


class ChatDatabase(BaseDatabase):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._init_db()

    def _init_db(self) -> None:
        with self._cursor() as cur:
            if cur is None:
                return
            # Drop and recreate tables to ensure correct schema
            cur.execute("DROP TABLE IF EXISTS chat_messages CASCADE;")
            cur.execute("DROP TABLE IF EXISTS chat_sessions CASCADE;")
            
            cur.execute(
                """
                CREATE TABLE chat_sessions (
                    id VARCHAR(255) PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            
            cur.execute(
                """
                CREATE TABLE chat_messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
                """
            )

    def save_message(self, session_id: str, role: str, content: str) -> None:
        with self._cursor() as cur:
            if cur is None:
                return
            cur.execute("SELECT id FROM chat_sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                title = content[:30] + ("..." if len(content) > 30 else "") if role == "user" else "Creative Assistant Chat"
                cur.execute("INSERT INTO chat_sessions (id, title) VALUES (%s, %s);", (session_id, title))
            cur.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content)
                VALUES (%s, %s, %s, %s);
                """,
                (str(uuid.uuid4()), session_id, role, content),
            )

    def get_history(self, session_id: str) -> list[dict]:
        with self._cursor() as cur:
            if cur is None:
                return []
            cur.execute(
                """
                SELECT role, content FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC;
                """,
                (session_id,),
            )
            return [{"role": row[0], "content": row[1]} for row in cur.fetchall()]

    def get_sessions(self) -> list[dict]:
        with self._cursor() as cur:
            if cur is None:
                return []
            cur.execute(
                """
                SELECT m.session_id, max(m.created_at) as last_activity, s.title
                FROM chat_messages m
                LEFT JOIN chat_sessions s ON m.session_id = s.id
                GROUP BY m.session_id, s.title
                ORDER BY last_activity DESC
                LIMIT 20;
                """
            )
            return [{"session_id": row[0], "last_activity": row[1].isoformat(), "title": row[2]} for row in cur.fetchall()]


class CampaignDatabase(BaseDatabase):
    def save_campaign(self, package: CampaignPackage) -> str | None:
        with self._cursor() as cur:
            if cur is None:
                return None
            try:
                cur.execute(
                    """
                    INSERT INTO creative_campaigns (
                        campaign_name, campaign_slug, brand_name, platform, objective,
                        input_data, hooks, angles, ad_copies, visual_concepts,
                        generated_creatives, scored_creatives, creative_assets
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id;
                    """,
                    (
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
                    ),
                )
                result = cur.fetchone()
                return result[0] if result else None
            except Exception as exc:
                logger.exception("Database save error: %s", exc)
                return None

    def get_campaigns(self, limit: int = 20) -> list[dict]:
        with self._cursor() as cur:
            if cur is None:
                return []
            try:
                cur.execute(
                    """
                    SELECT id, campaign_name, campaign_slug, brand_name, platform, objective, created_at
                    FROM creative_campaigns
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                columns = [desc[0] for desc in cur.description]
                results = []
                for row in cur.fetchall():
                    item = dict(zip(columns, row))
                    if item.get("created_at"):
                        item["created_at"] = item["created_at"].isoformat()
                    results.append(item)
                return results
            except Exception as exc:
                logger.exception("Database fetch error: %s", exc)
                return []
