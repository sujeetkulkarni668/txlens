"""FastAPI dependency enforcing real authentication — replaces the
Phase 5 placeholder (`get_current_user_id` used to be a hardcoded UUID;
see git history / earlier phase notes). Every endpoint that previously
depended on the placeholder now gets a real, JWT-verified user id, or a
401, with no code change needed at the call site.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import ExpiredTokenError, InvalidTokenError
from app.auth.tokens import get_user_id_from_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return get_user_id_from_token(credentials.credentials)
    except ExpiredTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
