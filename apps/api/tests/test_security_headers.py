import pytest
from starlette.requests import Request
from starlette.responses import Response
from app.core.security_headers import SecurityHeadersMiddleware

@pytest.mark.asyncio
async def test_security_headers_middleware_attaches_headers():
    middleware = SecurityHeadersMiddleware(app=None)

    async def call_next(request: Request) -> Response:
        return Response("ok", media_type="text/plain")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "scheme": "https",
        "server": ("localhost", 8000),
    }
    request = Request(scope)
    response = await middleware.dispatch(request, call_next)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Strict-Transport-Security" in response.headers
