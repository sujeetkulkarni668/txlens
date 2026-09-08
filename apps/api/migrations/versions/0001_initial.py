"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-07 00:00:00

Hand-authored (not `alembic revision --autogenerate`) — Alembic/SQLAlchemy
aren't installed in the environment that generated this repo, so
autogenerate could never be run against a real database connection.
Written by cross-referencing every column, type, nullability, default,
foreign key, and index against app/models/*.py directly (see that
directory's field definitions). NOT VERIFIED — ENVIRONMENT LIMITATION:
`alembic upgrade head` has never been run against a real PostgreSQL
instance. Table creation order respects foreign-key dependencies; the
downgrade() drops them in exact reverse order for the same reason.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("verified_wallet_address", sa.String(42), nullable=True),
        *_timestamp_columns(),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── wallets ────────────────────────────────────────────────────
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(42), nullable=False),
        sa.Column("chain", sa.String(64), nullable=False, server_default="base-sepolia"),
        sa.Column("first_seen_block", sa.Integer, nullable=True),
        sa.Column("transaction_count", sa.Integer, nullable=True),
        *_timestamp_columns(),
    )
    op.create_unique_constraint("uq_wallets_address", "wallets", ["address"])
    op.create_index("ix_wallets_address", "wallets", ["address"])

    # ── contracts ──────────────────────────────────────────────────
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(42), nullable=False),
        sa.Column("chain", sa.String(64), nullable=False, server_default="base-sepolia"),
        sa.Column("source_verified", sa.Boolean, nullable=True),
        sa.Column("abi", sa.JSON, nullable=True),
        sa.Column("abi_inferred", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("bytecode_available", sa.Boolean, nullable=True),
        sa.Column("deployed_block", sa.Integer, nullable=True),
        sa.Column("function_selectors", sa.JSON, nullable=True),
        sa.Column("admin_functions", sa.JSON, nullable=True),
        *_timestamp_columns(),
    )
    op.create_unique_constraint("uq_contracts_address", "contracts", ["address"])
    op.create_index("ix_contracts_address", "contracts", ["address"])

    # ── tokens ─────────────────────────────────────────────────────
    op.create_table(
        "tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(42), nullable=False),
        sa.Column("chain", sa.String(64), nullable=False, server_default="base-sepolia"),
        sa.Column("symbol", sa.String(32), nullable=True),
        sa.Column("decimals", sa.Integer, nullable=True),
        sa.Column("total_supply", sa.String(78), nullable=True),
        sa.Column("contract_verified", sa.Boolean, nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("risk_indicators", sa.JSON, nullable=True),
        *_timestamp_columns(),
    )
    op.create_unique_constraint("uq_tokens_address", "tokens", ["address"])
    op.create_index("ix_tokens_address", "tokens", ["address"])

    # ── transactions ───────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chain", sa.String(64), nullable=False, server_default="base-sepolia"),
        sa.Column("tx_hash", sa.String(66), nullable=True),
        sa.Column("from_address", sa.String(42), nullable=False),
        sa.Column("to_address", sa.String(42), nullable=True),
        sa.Column("value_wei", sa.String(78), nullable=False, server_default="0"),
        sa.Column("data", sa.String, nullable=True),
        sa.Column("tx_type", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("submitted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        *_timestamp_columns(),
    )
    op.create_unique_constraint("uq_transactions_tx_hash", "transactions", ["tx_hash"])
    op.create_index("ix_transactions_tx_hash", "transactions", ["tx_hash"])
    op.create_index("ix_transactions_from_address", "transactions", ["from_address"])
    op.create_index("ix_transactions_to_address", "transactions", ["to_address"])

    # ── transaction_analysis ───────────────────────────────────────
    op.create_table(
        "transaction_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
        ),
        sa.Column("decoded_function", sa.String(255), nullable=True),
        sa.Column("decoded_params", sa.JSON, nullable=True),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("ai_risk_assessment", sa.Text, nullable=True),
        sa.Column("ai_findings", sa.JSON, nullable=True),
        sa.Column("ai_potential_impact", sa.JSON, nullable=True),
        sa.Column("ai_recommendation", sa.String(16), nullable=True),
        sa.Column("ai_confidence", sa.Integer, nullable=True),
        *_timestamp_columns(),
    )
    op.create_unique_constraint(
        "uq_transaction_analysis_transaction_id", "transaction_analysis", ["transaction_id"]
    )

    # ── simulation_results ─────────────────────────────────────────
    op.create_table(
        "simulation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=False,
        ),
        sa.Column("success", sa.Boolean, nullable=True),
        sa.Column("gas_estimate", sa.String(78), nullable=True),
        sa.Column("decoded_actions", sa.JSON, nullable=True),
        sa.Column("asset_changes", sa.JSON, nullable=True),
        sa.Column("approvals", sa.JSON, nullable=True),
        sa.Column("events", sa.JSON, nullable=True),
        sa.Column("warnings", sa.JSON, nullable=True),
        sa.Column("trace_supported", sa.Boolean, nullable=True),
        *_timestamp_columns(),
    )
    op.create_unique_constraint(
        "uq_simulation_results_transaction_id", "simulation_results", ["transaction_id"]
    )

    # ── risk_scores ────────────────────────────────────────────────
    op.create_table(
        "risk_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id"), nullable=True),
        sa.Column(
            "contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=True
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=True,
        ),
        sa.Column("risk_score", sa.Integer, nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("model_is_demo_data", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("model_version", sa.String(64), nullable=True),
        *_timestamp_columns(),
    )

    # ── risk_signals ───────────────────────────────────────────────
    op.create_table(
        "risk_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "risk_score_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_scores.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("impact", sa.Integer, nullable=False),
        sa.Column("detail", sa.JSON, nullable=True),
        *_timestamp_columns(),
    )

    # ── policies ───────────────────────────────────────────────────
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(64), nullable=False),
        sa.Column("parameters", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        *_timestamp_columns(),
    )

    # ── security_reports ───────────────────────────────────────────
    op.create_table(
        "security_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("structured_evidence", sa.JSON, nullable=True),
        *_timestamp_columns(),
    )

    # ── mcp_tool_calls ─────────────────────────────────────────────
    op.create_table(
        "mcp_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("permission_class", sa.String(32), nullable=False),
        sa.Column("input_payload", sa.JSON, nullable=True),
        sa.Column("output_payload", sa.JSON, nullable=True),
        sa.Column("authorized", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("requested_by_user_id", sa.String(64), nullable=True),
        *_timestamp_columns(),
    )
    op.create_index("ix_mcp_tool_calls_tool_name", "mcp_tool_calls", ["tool_name"])

    # ── audit_logs ─────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", sa.String(64), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        *_timestamp_columns(),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])


def downgrade() -> None:
    # Reverse dependency order.
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_mcp_tool_calls_tool_name", table_name="mcp_tool_calls")
    op.drop_table("mcp_tool_calls")

    op.drop_table("security_reports")
    op.drop_table("policies")
    op.drop_table("risk_signals")
    op.drop_table("risk_scores")

    op.drop_table("simulation_results")
    op.drop_table("transaction_analysis")

    op.drop_index("ix_transactions_to_address", table_name="transactions")
    op.drop_index("ix_transactions_from_address", table_name="transactions")
    op.drop_index("ix_transactions_tx_hash", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_tokens_address", table_name="tokens")
    op.drop_table("tokens")

    op.drop_index("ix_contracts_address", table_name="contracts")
    op.drop_table("contracts")

    op.drop_index("ix_wallets_address", table_name="wallets")
    op.drop_table("wallets")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
