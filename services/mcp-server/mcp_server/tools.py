"""The 12 TxLens MCP tools (product spec section 16).

Every tool: calls the backend API only (never RPC/DB directly), is
audit-logged regardless of outcome, and returns a ToolResult rather than
raising — a failed backend call or a denied authorization is a normal,
structured outcome for a tool call, not an exceptional one.
"""
from __future__ import annotations

from mcp_server.audit import AuditLogger
from mcp_server.authorization import check_authorization
from mcp_server.client import TxLensAPIClient, TxLensAPIError
from mcp_server.schemas import AuditEntry, PermissionClass, ToolResult


async def _run_read_only(
    *, tool_name: str, client_call, input_payload: dict, audit: AuditLogger
) -> ToolResult:
    try:
        output = await client_call()
        result = ToolResult(
            tool_name=tool_name,
            permission_class=PermissionClass.READ_ONLY,
            success=True,
            authorized=True,
            output=output,
        )
    except TxLensAPIError as exc:
        result = ToolResult(
            tool_name=tool_name,
            permission_class=PermissionClass.READ_ONLY,
            success=False,
            authorized=True,
            error=exc.message,
        )
    await audit.record(
        AuditEntry(
            tool_name=tool_name,
            permission_class=PermissionClass.READ_ONLY,
            input_payload=input_payload,
            output_payload=result.output,
            authorized=True,
            error=result.error,
        )
    )
    return result


# ── read-only tools ──────────────────────────────────────────────────

async def inspect_wallet(client: TxLensAPIClient, audit: AuditLogger, *, address: str) -> ToolResult:
    return await _run_read_only(
        tool_name="inspect_wallet",
        client_call=lambda: client.get_wallet(address),
        input_payload={"address": address},
        audit=audit,
    )


async def get_wallet_transactions(
    client: TxLensAPIClient, audit: AuditLogger, *, address: str
) -> ToolResult:
    # No indexer/history service exists yet (product spec section 11) —
    # reported honestly as not implemented rather than silently returning
    # an empty list, which could be misread as "no transactions found".
    result = ToolResult(
        tool_name="get_wallet_transactions",
        permission_class=PermissionClass.READ_ONLY,
        success=False,
        authorized=True,
        error="not implemented: wallet transaction history requires an indexer, "
        "which this phase doesn't integrate",
    )
    await audit.record(
        AuditEntry(
            tool_name="get_wallet_transactions",
            permission_class=PermissionClass.READ_ONLY,
            input_payload={"address": address},
            output_payload=None,
            authorized=True,
            error=result.error,
        )
    )
    return result


async def inspect_contract(client: TxLensAPIClient, audit: AuditLogger, *, address: str) -> ToolResult:
    return await _run_read_only(
        tool_name="inspect_contract",
        client_call=lambda: client.get_contract(address),
        input_payload={"address": address},
        audit=audit,
    )


async def check_token(client: TxLensAPIClient, audit: AuditLogger, *, address: str) -> ToolResult:
    return await _run_read_only(
        tool_name="check_token",
        client_call=lambda: client.get_token(address),
        input_payload={"address": address},
        audit=audit,
    )


async def simulate_transaction(client: TxLensAPIClient, audit: AuditLogger, *, transaction: dict) -> ToolResult:
    return await _run_read_only(
        tool_name="simulate_transaction",
        client_call=lambda: client.simulate_transaction(transaction),
        input_payload={"transaction": transaction},
        audit=audit,
    )


async def trace_transaction(client: TxLensAPIClient, audit: AuditLogger, *, transaction: dict) -> ToolResult:
    """Implemented as a thin view over /transactions/simulate's trace
    output (events, asset_changes, trace_supported) rather than a
    separate backend endpoint — there's no additional capability to
    expose beyond what simulation already computes."""
    result = await _run_read_only(
        tool_name="trace_transaction",
        client_call=lambda: client.simulate_transaction(transaction),
        input_payload={"transaction": transaction},
        audit=audit,
    )
    if result.success and result.output is not None:
        full = result.output
        result.output = {
            "trace_supported": full.get("trace_supported"),
            "events": full.get("events", []),
            "asset_changes": full.get("asset_changes", []),
            "warnings": full.get("warnings", []),
        }
    return result


async def check_wallet_risk(client: TxLensAPIClient, audit: AuditLogger, *, address: str) -> ToolResult:
    # Deliberately not implemented — same reasoning as the backend's
    # GET /wallets/{address}/risk decision in Phase 4: without a specific
    # transaction for context, scoring would run on an almost entirely
    # imputed feature vector and risk looking more authoritative than it is.
    result = ToolResult(
        tool_name="check_wallet_risk",
        permission_class=PermissionClass.READ_ONLY,
        success=False,
        authorized=True,
        error="not implemented: standalone wallet risk scoring (without a specific "
        "transaction for context) is intentionally not offered — see README limitations",
    )
    await audit.record(
        AuditEntry(
            tool_name="check_wallet_risk", permission_class=PermissionClass.READ_ONLY,
            input_payload={"address": address}, output_payload=None, authorized=True, error=result.error,
        )
    )
    return result


async def check_contract_risk(client: TxLensAPIClient, audit: AuditLogger, *, address: str) -> ToolResult:
    result = ToolResult(
        tool_name="check_contract_risk",
        permission_class=PermissionClass.READ_ONLY,
        success=False,
        authorized=True,
        error="not implemented: contract-level risk scoring requires contract "
        "verification/history data this phase doesn't fetch",
    )
    await audit.record(
        AuditEntry(
            tool_name="check_contract_risk", permission_class=PermissionClass.READ_ONLY,
            input_payload={"address": address}, output_payload=None, authorized=True, error=result.error,
        )
    )
    return result


async def check_policy(client: TxLensAPIClient, audit: AuditLogger, *, transaction: dict) -> ToolResult:
    """Runs the full analyze pipeline and returns only the policy portion
    — reuses /transactions/analyze rather than duplicating policy-fetch
    logic in a separate endpoint."""
    result = await _run_read_only(
        tool_name="check_policy",
        client_call=lambda: client.analyze_transaction(transaction),
        input_payload={"transaction": transaction},
        audit=audit,
    )
    if result.success and result.output is not None:
        result.output = result.output.get("policy")
    return result


async def create_security_report(
    client: TxLensAPIClient, audit: AuditLogger, *, transaction: dict
) -> ToolResult:
    """No security_reports write endpoint exists yet (the DB model does,
    but Phase 7 doesn't add CRUD for it) — returns the full analysis as
    the report body rather than persisting it, and says so."""
    result = await _run_read_only(
        tool_name="create_security_report",
        client_call=lambda: client.analyze_transaction(transaction),
        input_payload={"transaction": transaction},
        audit=audit,
    )
    if result.success and result.output is not None:
        result.output = {
            "report": result.output,
            "persisted": False,
            "note": "POST /api/v1/reports does not exist yet — this report is "
            "returned inline, not saved",
        }
    return result


# ── sensitive tools (require explicit authorization) ────────────────

async def request_approval(
    client: TxLensAPIClient, audit: AuditLogger, *, transaction: dict, authorized: bool = False
) -> ToolResult:
    denial = check_authorization(permission_class=PermissionClass.SENSITIVE, authorized=authorized)
    if denial:
        result = ToolResult(
            tool_name="request_approval", permission_class=PermissionClass.SENSITIVE,
            success=False, authorized=False, error=denial,
        )
    else:
        # No approval-queue backend capability exists yet — authorization
        # succeeding doesn't mean there's anything to fulfill it with.
        result = ToolResult(
            tool_name="request_approval", permission_class=PermissionClass.SENSITIVE,
            success=False, authorized=True,
            error="authorized, but not implemented: there is no approval-queue "
            "backend capability yet",
        )
    await audit.record(
        AuditEntry(
            tool_name="request_approval", permission_class=PermissionClass.SENSITIVE,
            input_payload={"transaction": transaction}, output_payload=result.output,
            authorized=result.authorized, error=result.error,
        )
    )
    return result


async def create_policy(
    client: TxLensAPIClient,
    audit: AuditLogger,
    *,
    name: str,
    rule_type: str,
    parameters: dict,
    authorized: bool = False,
) -> ToolResult:
    denial = check_authorization(permission_class=PermissionClass.SENSITIVE, authorized=authorized)
    input_payload = {"name": name, "rule_type": rule_type, "parameters": parameters}
    if denial:
        result = ToolResult(
            tool_name="create_policy", permission_class=PermissionClass.SENSITIVE,
            success=False, authorized=False, error=denial,
        )
    else:
        try:
            output = await client.create_policy(
                {"name": name, "rule_type": rule_type, "parameters": parameters, "is_active": True}
            )
            result = ToolResult(
                tool_name="create_policy", permission_class=PermissionClass.SENSITIVE,
                success=True, authorized=True, output=output,
            )
        except TxLensAPIError as exc:
            result = ToolResult(
                tool_name="create_policy", permission_class=PermissionClass.SENSITIVE,
                success=False, authorized=True, error=exc.message,
            )
    await audit.record(
        AuditEntry(
            tool_name="create_policy", permission_class=PermissionClass.SENSITIVE,
            input_payload=input_payload, output_payload=result.output,
            authorized=result.authorized, error=result.error,
        )
    )
    return result
