"""Audit trail of every MCP tool invocation (section 16 / 28).

Every MCP tool call is recorded here regardless of outcome — required for
permission-boundary auditing and prompt-injection forensics.
"""
from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class McpToolCall(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "mcp_tool_calls"

    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    permission_class: Mapped[str] = mapped_column(String(32), nullable=False)  # read_only|sensitive
    input_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    authorized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
