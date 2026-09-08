"""Audit logging for MCP tool invocations (product spec section 16, 28) —
every call is recorded, success or failure, authorized or not.

AuditLogger is an interface so the MCP server can log to the backend's
mcp_tool_calls table in production while tests use InMemoryAuditLogger.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from mcp_server.schemas import AuditEntry


class AuditLogger(ABC):
    @abstractmethod
    async def record(self, entry: AuditEntry) -> None: ...


class InMemoryAuditLogger(AuditLogger):
    """Used by tests and for local/dev runs without a database
    connection. A production deployment should back this with a real
    logger that writes to the mcp_tool_calls table."""

    def __init__(self):
        self.entries: list[AuditEntry] = []

    async def record(self, entry: AuditEntry) -> None:
        self.entries.append(entry)
