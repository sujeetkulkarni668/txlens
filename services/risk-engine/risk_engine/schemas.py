"""Risk engine output types (product spec section 14).

Stdlib dataclass — same rationale as the parser/simulation modules: keeps
this service importable without pulling in the web framework stack.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskSignal:
    name: str
    impact: int  # contribution, in score points; can be negative (risk-reducing)


@dataclass
class RiskAssessment:
    risk_score: int  # 0-100
    risk_level: str  # LOW | MEDIUM | HIGH | CRITICAL
    signals: list[RiskSignal] = field(default_factory=list)

    model_is_demo_data: bool = True
    model_version: str = "unknown"
    model_confidence: float = 1.0  # 0..1, reduced when features were imputed
    notes: list[str] = field(default_factory=list)
