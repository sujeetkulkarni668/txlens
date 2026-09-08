"""API request/response schemas for policy CRUD and evaluation results."""
import uuid

from pydantic import BaseModel, Field

from app.policy.schemas import PolicyDecision, RuleType


class PolicyCreate(BaseModel):
    name: str
    rule_type: RuleType
    parameters: dict = Field(default_factory=dict)
    is_active: bool = True


class PolicyUpdate(BaseModel):
    name: str | None = None
    rule_type: RuleType | None = None
    parameters: dict | None = None
    is_active: bool | None = None


class PolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    rule_type: RuleType
    parameters: dict
    is_active: bool

    model_config = {"from_attributes": True}


class RuleOutcomeResponse(BaseModel):
    rule_name: str
    rule_type: str
    decision: PolicyDecision | None
    reason: str


class PolicyEvaluationResponse(BaseModel):
    decision: PolicyDecision
    matched_rules: list[RuleOutcomeResponse] = Field(default_factory=list)
    unevaluated_rules: list[RuleOutcomeResponse] = Field(default_factory=list)
