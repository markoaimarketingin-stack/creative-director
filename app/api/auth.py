from fastapi import Request, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests
from app.core.config import get_settings

def verify_google_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split(" ")[1]
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="Google Client ID not configured")
        
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.google_client_id)
        # Ensure the token has the expected payload
        if 'email' not in idinfo:
            raise HTTPException(status_code=401, detail="Token does not contain an email")
        return idinfo['email']
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
