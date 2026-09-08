"""TxLens API entrypoint.

Security hardening wired here (product spec section 26): CORS, rate
limiting, structured error responses that never leak internals, and a
startup check that refuses to run with a default/insecure secret key in
production. Business endpoints live behind app/api/v1/router.py.
"""
import logging

import structlog
from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as v1_router
from app.core.body_limit import BodySizeLimitMiddleware
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.health import check_database, check_redis
from app.core.rate_limit import limiter
from app.db.session import get_db

settings = get_settings()
logger = structlog.get_logger()

# Fail loudly rather than silently running a production deployment with a
# guessable JWT signing key. Development/test environments only warn, so
# `uvicorn app.main:app --reload` against .env.example still works.
_secret_problems = settings.insecure_defaults()
if _secret_problems:
    for problem in _secret_problems:
        if settings.is_production:
            raise RuntimeError(f"refusing to start in production: {problem}")
        logging.getLogger(__name__).warning("insecure configuration (dev-only): %s", problem)

app = FastAPI(
    title="TxLens API",
    description="Pre-transaction blockchain security and intelligence platform.",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BodySizeLimitMiddleware)

app.include_router(v1_router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness probe — process is up."""
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def ready(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe — actually checks dependencies rather than
    claiming "ok" unconditionally. Returns a real DB round-trip result
    and a real Redis PING result; overall status is only "ok" when both
    are. Sets a 503 status code when not ready, so this is usable
    directly as a Kubernetes-style readiness probe, not just an
    informational payload a caller has to parse to find out the truth.
    """
    db_status = await check_database(db)
    redis_status = await check_redis()
    overall_ok = db_status == "ok" and redis_status == "ok"
    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if overall_ok else "not_ready",
        "checks": {"db": db_status, "redis": redis_status},
    }
