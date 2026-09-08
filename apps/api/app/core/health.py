"""Real dependency checks for the readiness probe (product spec section
18 / this review's explicit requirement: "/ready must verify required
dependencies... do not return ok while dependencies are known to be
unavailable").

NOT executed in the environment that generated this repo — no running
Postgres/Redis to check against, and the driver packages
(asyncpg/redis) aren't installed (no network). Syntax-checked only, same
as the rest of the FastAPI/SQLAlchemy layer. This is a genuine behavior
change from the earlier `/ready` implementation, which always returned
"ok" regardless of whether anything downstream was actually reachable.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings


async def check_database(db: AsyncSession) -> str:
    """Returns "ok" only after a real round-trip query succeeds."""
    try:
        await db.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001 — any DB failure means "not ok", full stop
        return f"unavailable: {exc}"


async def check_redis() -> str:
    settings = get_settings()
    try:
        import redis.asyncio as redis_asyncio

        client = redis_asyncio.from_url(settings.redis_url, socket_connect_timeout=2)
        try:
            await client.ping()
            return "ok"
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"
