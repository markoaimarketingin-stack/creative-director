from fastapi import Header, HTTPException
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import get_settings


def require_api_auth(authorization: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.api_auth_enabled:
        return "anonymous"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    token = authorization.split(" ", 1)[1].strip()
    if settings.app_api_key and token == settings.app_api_key:
        return "service-account"

    if settings.google_client_id:
        try:
            payload = id_token.verify_oauth2_token(token, requests.Request(), settings.google_client_id)
            email = payload.get("email")
            if email:
                return email
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    raise HTTPException(status_code=401, detail="Unauthorized.")
