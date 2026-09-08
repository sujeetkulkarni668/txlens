# mcp-server

Dedicated TxLens MCP server (product spec section 16) — all 12 tools:
10 read-only (`inspect_wallet`, `get_wallet_transactions`,
`inspect_contract`, `check_token`, `simulate_transaction`,
`trace_transaction`, `check_wallet_risk`, `check_contract_risk`,
`check_policy`, `create_security_report`) and 2 sensitive
(`request_approval`, `create_policy`, both gated behind explicit
`authorized=true`).

## Design

- **Never bypasses the backend.** Every tool calls the TxLens API
  (`mcp_server/client.py`, stdlib `urllib`) — never the blockchain RPC or
  the database directly. No private keys ever touch this service.
- **Every call is audited**, success or failure, authorized or denied
  (`mcp_server/audit.py`). `InMemoryAuditLogger` is used for tests/local
  dev; production should back this with the `mcp_tool_calls` table.
- **Sensitive tools always require `authorized=true`**
  (`mcp_server/authorization.py`) — set by whatever is upstream of the
  tool call. This module doesn't claim to know *how* that confirmation
  was obtained; it only guarantees the call never executes without it.
- **Honest about capability gaps.** `get_wallet_transactions`,
  `check_wallet_risk`, and `check_contract_risk` all return a structured
  "not implemented" result rather than a fabricated or empty-looking
  one — each depends on an indexer/contract-verification service this
  project doesn't have yet.

## What's real vs. syntax-checked only

`client.py`, `authorization.py`, `audit.py`, and `tools.py` — the actual
tool logic — are dependency-free and **genuinely tested**: 19 passing
tests (`tests/test_client.py`, `test_authorization.py`, `test_tools.py`)
using a hand-written fake API client, no network needed.

`server.py` (the MCP protocol transport wiring using the `mcp` SDK) is
**syntax-checked only** — the package isn't installed and there's no
network to install it in the environment that generated this repo.

## Run it (once `mcp` is installed and the API is running)

```bash
pip install -r requirements.txt
TXLENS_API_URL=http://localhost:8000 python -m mcp_server.server
```
