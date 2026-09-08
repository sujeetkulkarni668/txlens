"""API response schema for the AI analyst stage."""
from pydantic import BaseModel, Field


class AIAssessmentResponse(BaseModel):
    summary: str
    risk_assessment: str
    findings: list[str] = Field(default_factory=list)
    potential_impact: list[str] = Field(default_factory=list)
    recommendation: str
    confidence: int
    is_fallback: bool = False
    notes: list[str] = Field(default_factory=list)
