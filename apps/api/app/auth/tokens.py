"""Issues/verifies access tokens for the API, using the stdlib JWT
implementation in jwt.py with this app's configured secret key."""
from __future__ import annotations

from app.auth.jwt import decode_jwt, encode_jwt
from app.core.config import get_settings

ACCESS_TOKEN_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    return encode_jwt({"sub": user_id}, settings.api_secret_key, expires_in_seconds=ACCESS_TOKEN_TTL_SECONDS)


def get_user_id_from_token(token: str) -> str:
    """Raises app.auth.jwt.InvalidTokenError (or ExpiredTokenError) on any
    problem — callers (the FastAPI dependency) turn that into a 401."""
    settings = get_settings()
    claims = decode_jwt(token, settings.api_secret_key)
    subject = claims.get("sub")
    if not subject:
        from app.auth.jwt import InvalidTokenError

        raise InvalidTokenError("token has no 'sub' claim")
    return subject
