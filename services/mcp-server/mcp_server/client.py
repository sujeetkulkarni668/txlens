"""HTTP client for calling the TxLens backend API from the MCP server.

Uses stdlib urllib (not httpx): keeps this module dependency-free and
fully unit-testable (mocking urllib.request.urlopen) without installing
anything, matching the pattern used for EVMRPCProvider in Phase 2. The
MCP server never talks to the blockchain RPC, the database, or the AI
provider directly — every tool goes through this client to the backend
API (product spec section 16: "It should NOT bypass the backend").

Since Phase 11, most backend endpoints require a bearer token (see
apps/api/app/auth/) — pass one via `api_token` or `set_api_token()`.
Read-only public endpoints (health, wallet/contract/token lookups) don't
require it, but `/transactions/analyze` and all `/policies` endpoints do.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class TxLensAPIError(Exception):
    def __init__(self, status_code: int | None, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"TxLens API error ({status_code}): {message}")


class TxLensAPIClient:
    def __init__(self, base_url: str, *, api_token: str | None = None, timeout_seconds: float = 15.0):
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds

    def set_api_token(self, token: str | None) -> None:
        """Update the bearer token used for subsequent requests — e.g.
        after the MCP server itself authenticates on the caller's behalf,
        or when a session token is refreshed."""
        self._api_token = token

    def _sync_request(self, method: str, path: str, body: dict | None) -> Any:
        url = f"{self._base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(error_body).get("detail", error_body)
            except json.JSONDecodeError:
                detail = error_body
            raise TxLensAPIError(exc.code, str(detail)) from exc
        except urllib.error.URLError as exc:
            raise TxLensAPIError(None, f"could not reach TxLens API at {url}: {exc}") from exc

        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TxLensAPIError(None, f"non-JSON response from {url}: {exc}") from exc

    async def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        import asyncio

        return await asyncio.to_thread(self._sync_request, method, path, body)

    # ── endpoints the MCP tools need ──────────────────────────────────

    async def analyze_transaction(self, tx: dict) -> dict:
        return await self._request("POST", "/api/v1/transactions/analyze", tx)

    async def simulate_transaction(self, tx: dict) -> dict:
        return await self._request("POST", "/api/v1/transactions/simulate", tx)

    async def get_wallet(self, address: str) -> dict:
        return await self._request("GET", f"/api/v1/wallets/{address}")

    async def get_contract(self, address: str) -> dict:
        return await self._request("GET", f"/api/v1/contracts/{address}")

    async def get_token(self, address: str) -> dict:
        return await self._request("GET", f"/api/v1/tokens/{address}")

    async def get_transaction(self, tx_hash: str) -> dict:
        return await self._request("GET", f"/api/v1/transactions/{tx_hash}")

    async def list_policies(self) -> list[dict]:
        return await self._request("GET", "/api/v1/policies")

    async def create_policy(self, policy: dict) -> dict:
        return await self._request("POST", "/api/v1/policies", policy)
