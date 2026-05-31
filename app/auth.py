import os
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import get_settings

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security)
) -> dict:
    """
    Validates the JWT token issued by the Marko Auth Service.
    Returns the decoded payload containing user_id and username.
    Raises 401 if token is invalid or expired.

    If api_auth_enabled is False, this acts as a fallback to guest user
    to prevent breaking local development / guest workflows.
    """
    settings = get_settings()
    jwt_secret = os.getenv("JWT_SECRET") or settings.jwt_secret
    jwt_algorithm = os.getenv("JWT_ALGORITHM") or settings.jwt_algorithm or "HS256"

    if not credentials:
        if not settings.api_auth_enabled:
            return {
                "user_id": "00000000-0000-0000-0000-000000000000",
                "username": "guest@marko.ai",
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header."
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])

        user_id: str = payload.get("user_id")
        username: str = payload.get("sub")  # sub contains the username

        if not user_id or not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure: missing user_id or sub"
            )

        return {
            "user_id": user_id,
            "username": username,
        }

    except JWTError as e:
        if not settings.api_auth_enabled:
            return {
                "user_id": "00000000-0000-0000-0000-000000000000",
                "username": "guest@marko.ai",
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
