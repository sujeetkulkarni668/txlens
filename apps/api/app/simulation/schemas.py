"""Simulation service output (product spec section 10).

Stdlib dataclass, matching the DB model (app/models/simulation_result.py)
field-for-field, and mirroring the honesty pattern used by the parser: an
explicit `trace_supported` flag rather than silently returning empty
asset_changes/events when the RPC endpoint can't provide them.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimulationResult:
    # None means "could not be determined" — distinct from False.
    success: bool | None
    gas_estimate: str | None

    decoded_actions: list[dict] = field(default_factory=list)
    asset_changes: list[dict] = field(default_factory=list)
    approvals: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    trace_supported: bool | None = None
