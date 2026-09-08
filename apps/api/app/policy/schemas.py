"""Policy engine types (product spec section 18).

Stdlib dataclasses — same rationale as parser/simulation/risk: keeps the
engine importable and unit-testable without the web/DB stack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


# Severity ordering used to combine multiple rule outcomes into one
# overall decision — the most severe matched outcome wins.
_SEVERITY = {PolicyDecision.ALLOW: 0, PolicyDecision.REVIEW: 1, PolicyDecision.BLOCK: 2}


class RuleType(str, Enum):
    MAXIMUM_TRANSACTION_VALUE = "maximum_transaction_value"
    MAXIMUM_DAILY_SPEND = "maximum_daily_spend"
    REQUIRE_REVIEW_ABOVE = "require_review_above"
    BLOCK_UNLIMITED_APPROVALS = "block_unlimited_approvals"
    BLOCK_UNKNOWN_CONTRACTS = "block_unknown_contracts"
    REQUIRE_REVIEW_FOR_NEW_CONTRACTS = "require_review_for_new_contracts"


@dataclass
class PolicyRule:
    """One user-defined policy (mirrors app/models/policy.py)."""

    name: str
    rule_type: RuleType
    parameters: dict
    is_active: bool = True


@dataclass
class PolicyEvaluationContext:
    """Everything the engine might need to evaluate a rule against — each
    field is Optional because upstream data (contract intelligence, spend
    history) may not be available yet; the engine must say so rather than
    guess (product spec section 34)."""

    transaction_value_native: float
    is_unlimited_approval: bool = False

    # None = "unknown", not "no" / "0" — see engine docstring.
    contract_known: bool | None = None
    contract_age_days: float | None = None
    daily_spend_so_far_native: float | None = None


@dataclass
class RuleOutcome:
    rule_name: str
    rule_type: RuleType
    decision: PolicyDecision | None  # None means "could not be evaluated"
    reason: str


@dataclass
class PolicyEvaluationResult:
    decision: PolicyDecision
    matched_rules: list[RuleOutcome] = field(default_factory=list)
    unevaluated_rules: list[RuleOutcome] = field(default_factory=list)
