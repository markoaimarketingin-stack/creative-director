from supabase import create_client, Client
from app.core.config import Settings


def get_supabase_client(settings: Settings) -> Client | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)