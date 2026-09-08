"""API response schema for risk assessment."""
from pydantic import BaseModel, Field


class RiskSignalResponse(BaseModel):
    name: str
    impact: int


class RiskAssessmentResponse(BaseModel):
    risk_score: int
    risk_level: str
    signals: list[RiskSignalResponse] = Field(default_factory=list)
    model_is_demo_data: bool = True
    model_version: str
    model_confidence: float
    notes: list[str] = Field(default_factory=list)
