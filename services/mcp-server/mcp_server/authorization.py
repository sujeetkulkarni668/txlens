"""Authorization gate for sensitive MCP tools (product spec section 16).

Deliberately simple: a sensitive tool call must carry an explicit
`authorized=True` argument, set by whatever is upstream of the MCP tool
call (the AI agent's tool-call arguments, ultimately reflecting the
client surface's confirmation UX). This module makes no claim about
*how* that confirmation was obtained — a production deployment should
tie `authorized` to a real human-in-the-loop confirmation step, not let
the AI agent set it unilaterally. What this module guarantees is narrower
but load-bearing: a sensitive tool NEVER executes without that flag set,
and every denial is reported back structurally, not raised as a bare
exception.
"""
from __future__ import annotations

from mcp_server.schemas import PermissionClass


def check_authorization(*, permission_class: PermissionClass, authorized: bool) -> str | None:
    """Returns None if the call may proceed, or a denial reason string if
    not."""
    if permission_class == PermissionClass.READ_ONLY:
        return None
    if authorized:
        return None
    return (
        "sensitive operation requires explicit authorization — call again with "
        "authorized=true once the human has confirmed this action"
    )
