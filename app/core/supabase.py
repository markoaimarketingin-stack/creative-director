import psycopg2
from psycopg2.extensions import connection
from app.core.config import Settings


def get_db_connection(settings: Settings) -> connection | None:
    url = settings.supabase_url
    
    if not url or not url.startswith("postgresql://"):
        return None
        
    try:
        conn = psycopg2.connect(url)
        # Ensure changes are committed automatically or handle it manually
        conn.autocommit = True
        return conn
    except Exception as exc:
        print(f"[ERROR] Failed to connect to PostgreSQL database: {exc}")
        return None