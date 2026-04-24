from supabase import create_client, Client
from app.core.config import Settings


def get_supabase_client(settings: Settings) -> Client | None:
    url = settings.supabase_url
    key = settings.supabase_service_role_key
    
    if not url or not key:
        return None
        
    # Skip if they look like placeholders from .env.example
    if "your-project" in url or "your_supabase" in key:
        print("[INFO] Supabase placeholders detected. Skipping database initialization.")
        return None
        
    try:
        return create_client(url, key)
    except Exception as exc:
        print(f"[ERROR] Failed to initialize Supabase client: {exc}")
        return None