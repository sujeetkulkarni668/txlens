"""API request/response schemas for transaction endpoints."""
import uuid

from pydantic import BaseModel, Field

from app.parser.schemas import DecodeStatus, TransactionType
from app.schemas.ai_assessment import AIAssessmentResponse
from app.schemas.common import TransactionInput
from app.schemas.policy import PolicyEvaluationResponse
from app.schemas.risk import RiskAssessmentResponse
from app.schemas.simulation import SimulationResponse


class TransactionAnalyzeRequest(TransactionInput):
    """Same envelope as /transactions/simulate (product spec section 10)."""


class ParsedTransactionResponse(BaseModel):
    tx_type: TransactionType
    decode_status: DecodeStatus
    decoded_function: str | None = None
    contract_address: str | None = None
    parameters: dict[str, str] | None = None
    token_amount: str | None = None
    spender: str | None = None
    recipient: str | None = None
    sender: str | None = None
    is_unlimited_approval: bool = False
    notes: list[str] = Field(default_factory=list)


class TransactionAnalyzeResponse(BaseModel):
    """Pipeline stages not yet implemented are explicitly reported as such
    rather than silently omitted, per the critical honesty rule (product
    spec section 34) — a caller should never have to guess whether
    risk/policy/AI ran.
    """

    parsed: ParsedTransactionResponse
    simulation: SimulationResponse | None = None
    risk: RiskAssessmentResponse | None = None
    policy: PolicyEvaluationResponse | None = None
    ai_assessment: AIAssessmentResponse | None = None
    analysis_id: uuid.UUID | None = Field(
        default=None,
        description="Set once persisted to the database; null if persistence failed or was skipped.",
    )
    pipeline_status: dict[str, str] = Field(
        default_factory=lambda: {
            "parser": "complete",
            "simulation": "complete",
            "ml_risk": "complete",
            "policy": "complete",
            "ai_analyst": "complete",
            "persistence": "pending",
        }
    )
