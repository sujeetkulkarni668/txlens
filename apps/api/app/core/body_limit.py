"""Request body size limit middleware — nothing in this application
enforced one before (Starlette/FastAPI don't by default), which is a
real, unbounded-memory DoS vector for any JSON POST endpoint
(/transactions/analyze, /transactions/simulate, /policies, /auth/*).

NOT executed in the environment that generated this repo — Starlette
isn't installed (no network). Syntax-checked only.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

DEFAULT_MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MiB — every real request body
# this API accepts (a transaction envelope, a policy definition, login
# credentials) is a few KB at most; 1 MiB is generous headroom, not a
# tight fit, so legitimate requests are never at risk of hitting it.


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int = DEFAULT_MAX_BODY_BYTES):
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"message": f"request body exceeds {self._max_bytes} byte limit"},
                    )
            except ValueError:
                pass  # malformed header — let the framework's own parsing reject it
        return await call_next(request)
