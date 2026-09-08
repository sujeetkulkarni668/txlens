"""API response schema for /transactions/simulate."""
from pydantic import BaseModel, Field


class SimulationResponse(BaseModel):
    success: bool | None
    gas_estimate: str | None
    decoded_actions: list[dict] = Field(default_factory=list)
    asset_changes: list[dict] = Field(default_factory=list)
    approvals: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_supported: bool | None = None
