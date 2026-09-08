"""MCP protocol wiring — registers the 12 tools from tools.py with the
official MCP Python SDK.

NOT executed in the environment that generated this repo: the `mcp`
package isn't installed and there's no network to install it.
Syntax-checked only. The tool handlers themselves (tools.py) are fully
tested independently of this transport layer — see tests/test_tools.py.
"""
from __future__ import annotations

import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

import mcp_server.tools as tool_handlers
from mcp_server.audit import InMemoryAuditLogger
from mcp_server.client import TxLensAPIClient

TOOL_SCHEMAS: list[Tool] = [
    Tool(
        name="inspect_wallet",
        description="Look up public balance and nonce for an EVM wallet address.",
        inputSchema={
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
        },
    ),
    Tool(
        name="get_wallet_transactions",
        description="Get recent transaction history for a wallet. NOT YET IMPLEMENTED "
        "(requires an indexer) — will return a structured not-implemented error.",
        inputSchema={
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
        },
    ),
    Tool(
        name="inspect_contract",
        description="Check whether an address is a contract and report bytecode size. "
        "Source verification is not available this phase.",
        inputSchema={
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
        },
    ),
    Tool(
        name="check_token",
        description="Read an ERC-20 token's symbol, name, decimals, and total supply "
        "directly from the chain.",
        inputSchema={
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
        },
    ),
    Tool(
        name="simulate_transaction",
        description="Simulate an unsigned transaction: success/revert, gas estimate, and "
        "(when the RPC endpoint supports tracing) internal calls, events, and asset changes.",
        inputSchema={
            "type": "object",
            "properties": {
                "transaction": {
                    "type": "object",
                    "properties": {
                        "chain": {"type": "string"}, "from": {"type": "string"},
                        "to": {"type": "string"}, "value": {"type": "string"},
                        "data": {"type": "string"},
                    },
                    "required": ["from"],
                }
            },
            "required": ["transaction"],
        },
    ),
    Tool(
        name="trace_transaction",
        description="Get the internal-call trace (events, asset changes) for an unsigned "
        "transaction, if the RPC endpoint supports it.",
        inputSchema={
            "type": "object",
            "properties": {"transaction": {"type": "object"}},
            "required": ["transaction"],
        },
    ),
    Tool(
        name="check_wallet_risk",
        description="NOT IMPLEMENTED: standalone wallet risk scoring without transaction "
        "context is intentionally not offered.",
        inputSchema={
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
        },
    ),
    Tool(
        name="check_contract_risk",
        description="NOT IMPLEMENTED: requires contract verification/history data this "
        "phase doesn't fetch.",
        inputSchema={
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
        },
    ),
    Tool(
        name="check_policy",
        description="Evaluate an unsigned transaction against the caller's active policies.",
        inputSchema={
            "type": "object",
            "properties": {"transaction": {"type": "object"}},
            "required": ["transaction"],
        },
    ),
    Tool(
        name="create_security_report",
        description="Run full transaction analysis and return it as a report. Not yet "
        "persisted server-side (no reports write endpoint exists).",
        inputSchema={
            "type": "object",
            "properties": {"transaction": {"type": "object"}},
            "required": ["transaction"],
        },
    ),
    Tool(
        name="request_approval",
        description="SENSITIVE — requires authorized=true. Requests human approval for a "
        "flagged transaction. NOT YET IMPLEMENTED (no approval-queue backend exists).",
        inputSchema={
            "type": "object",
            "properties": {
                "transaction": {"type": "object"}, "authorized": {"type": "boolean"},
            },
            "required": ["transaction"],
        },
    ),
    Tool(
        name="create_policy",
        description="SENSITIVE — requires authorized=true. Creates a new user security "
        "policy.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "rule_type": {"type": "string"},
                "parameters": {"type": "object"},
                "authorized": {"type": "boolean"},
            },
            "required": ["name", "rule_type", "parameters"],
        },
    ),
]

_TOOL_FUNCS = {
    "inspect_wallet": tool_handlers.inspect_wallet,
    "get_wallet_transactions": tool_handlers.get_wallet_transactions,
    "inspect_contract": tool_handlers.inspect_contract,
    "check_token": tool_handlers.check_token,
    "simulate_transaction": tool_handlers.simulate_transaction,
    "trace_transaction": tool_handlers.trace_transaction,
    "check_wallet_risk": tool_handlers.check_wallet_risk,
    "check_contract_risk": tool_handlers.check_contract_risk,
    "check_policy": tool_handlers.check_policy,
    "create_security_report": tool_handlers.create_security_report,
    "request_approval": tool_handlers.request_approval,
    "create_policy": tool_handlers.create_policy,
}


def build_server() -> Server:
    app = Server("txlens-mcp-server")
    client = TxLensAPIClient(
        os.environ.get("TXLENS_API_URL", "http://localhost:8000"),
        api_token=os.environ.get("TXLENS_API_TOKEN"),
    )
    audit = InMemoryAuditLogger()  # production: back this with the mcp_tool_calls table

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOL_SCHEMAS

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        handler = _TOOL_FUNCS.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"unknown tool: {name}")]
        result = await handler(client, audit, **arguments)
        import json

        return [TextContent(type="text", text=json.dumps(result.__dict__, default=str))]

    return app


async def main() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
