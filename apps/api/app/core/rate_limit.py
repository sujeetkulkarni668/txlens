"""Rate limiting (product spec section 26) via slowapi.

NOT executed in the environment that generated this repo — slowapi isn't
installed (no network access). Syntax-checked only, same as the rest of
the FastAPI layer. Limits below are deliberately generous defaults for a
single-instance deployment; tune via RATE_LIMIT_PER_MINUTE for the
general case, and per-route `@limiter.limit(...)` overrides (see
endpoints/auth.py) for anything more brute-force-sensitive than the
default.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)
