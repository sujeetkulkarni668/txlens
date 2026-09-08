"""MCP tool result / audit types (product spec section 16, 28)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PermissionClass(str, Enum):
    READ_ONLY = "read_only"
    SENSITIVE = "sensitive"


@dataclass
class ToolResult:
    """What every tool handler returns — always, even on failure or a
    denied authorization, so the caller and the audit log get a
    consistent shape rather than a raised exception some of the time."""

    tool_name: str
    permission_class: PermissionClass
    success: bool
    authorized: bool
    output: dict | None = None
    error: str | None = None


@dataclass
class AuditEntry:
    tool_name: str
    permission_class: PermissionClass
    input_payload: dict
    output_payload: dict | None
    authorized: bool
    error: str | None = None
