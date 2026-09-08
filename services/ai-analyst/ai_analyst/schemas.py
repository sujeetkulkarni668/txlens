"""AI analyst evidence input and assessment output types (product spec
section 15). Stdlib dataclasses — no framework dependency."""
from __future__ import annotations

from dataclasses import dataclass, field

VALID_RECOMMENDATIONS = ("ALLOW", "REVIEW", "BLOCK")


@dataclass
class Evidence:
    """Everything the AI analyst is allowed to reason from. Optional
    fields are None, not fabricated placeholders, when a stage hasn't run
    or a fact isn't known — the prompt builder must represent that
    honestly rather than omit it silently."""

    transaction: dict
    parsed: dict
    simulation: dict | None = None
    risk: dict | None = None
    policy: dict | None = None
    # Not fetched by any service yet (sections 11-13 aren't implemented) —
    # always None today; included so the evidence shape and prompt don't
    # need to change once they exist.
    wallet_intelligence: dict | None = None
    contract_intelligence: dict | None = None
    token_intelligence: dict | None = None


@dataclass
class AIAssessment:
    summary: str
    risk_assessment: str
    findings: list[str] = field(default_factory=list)
    potential_impact: list[str] = field(default_factory=list)
    recommendation: str = "REVIEW"  # ALLOW | REVIEW | BLOCK
    confidence: int = 0  # 0-100

    # True when this is a safe-default produced because the model's raw
    # output couldn't be validated — never presented as a real assessment.
    is_fallback: bool = False
    notes: list[str] = field(default_factory=list)
