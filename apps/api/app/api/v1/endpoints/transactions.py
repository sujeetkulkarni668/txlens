"""POST /api/v1/transactions/analyze.

Runs every stage implemented so far — parsing (Phase 2), simulation
(Phase 3), ML risk scoring (Phase 4), policy evaluation (Phase 5), the AI
analyst (Phase 6, when AI_API_KEY is configured) — and persists the
result (Phase 10), reporting each stage's status explicitly via
`pipeline_status` rather than omitting or faking one. Persistence
failures are logged but never mask a completed analysis: the caller still
gets their result even if the audit-trail write fails, with
`analysis_id: null` and `pipeline_status.persistence` explaining why.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import (
    get_ai_analyst_service,
    get_current_user_id,
    get_policy_engine,
    get_risk_engine_service,
    get_simulation_service,
)
from app.db.session import get_db
from app.models.policy import Policy
from app.parser.parser import TransactionParser
from app.persistence.analysis_repository import save_analysis
from app.policy.engine import PolicyEngine
from app.policy.schemas import PolicyEvaluationContext, PolicyRule, RuleType
from app.schemas.ai_assessment import AIAssessmentResponse
from app.schemas.common import TransactionInput
from app.schemas.policy import PolicyEvaluationResponse, RuleOutcomeResponse
from app.schemas.risk import RiskAssessmentResponse, RiskSignalResponse
from app.schemas.simulation import SimulationResponse
from app.schemas.transaction import (
    ParsedTransactionResponse,
    TransactionAnalyzeResponse,
)
from app.simulation.service import SimulationService

router = APIRouter(prefix="/transactions", tags=["transactions"])
logger = logging.getLogger(__name__)

_parser = TransactionParser()

MAX_UINT256 = 2**256 - 1
WEI_PER_ETHER = 10**18


@router.post("/analyze", response_model=TransactionAnalyzeResponse)
async def analyze_transaction(
    request: TransactionInput,
    simulation_service: SimulationService = Depends(get_simulation_service),
    risk_service=Depends(get_risk_engine_service),
    policy_engine: PolicyEngine = Depends(get_policy_engine),
    ai_service=Depends(get_ai_analyst_service),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> TransactionAnalyzeResponse:
    parsed = _parser.parse(to=request.to, value=request.value, data=request.data)
    simulation = await simulation_service.simulate(
        chain=request.chain,
        from_address=request.from_address,
        to=request.to,
        value=request.value,
        data=request.data,
    )

    try:
        value_native = int(request.value) / WEI_PER_ETHER
    except (ValueError, TypeError):
        value_native = 0.0
    approval_ratio = (
        int(parsed.token_amount) / MAX_UINT256 if parsed.token_amount is not None else 0.0
    )

    risk = risk_service.assess_from_pipeline(
        transaction_type=parsed.tx_type.value,
        transaction_value_native=value_native,
        simulation_warning_count=len(simulation.warnings),
        approval_ratio_to_max=approval_ratio,
        is_unlimited_approval=parsed.is_unlimited_approval,
    )

    db_policies = await db.execute(
        select(Policy).where(Policy.owner_id == user_id, Policy.is_active.is_(True))
    )
    policy_rules = [
        PolicyRule(
            name=p.name, rule_type=RuleType(p.rule_type), parameters=p.parameters, is_active=p.is_active
        )
        for p in db_policies.scalars().all()
    ]
    # contract_known / contract_age_days / daily_spend_so_far_native are
    # genuinely unavailable this phase (no contract intelligence or
    # persistent spend tracking yet) — passed as None so the engine
    # reports those specific rules as unevaluated rather than guessing.
    policy_result = policy_engine.evaluate(
        policy_rules,
        PolicyEvaluationContext(
            transaction_value_native=value_native,
            is_unlimited_approval=parsed.is_unlimited_approval,
        ),
    )

    parsed_response = ParsedTransactionResponse(**parsed.__dict__)
    simulation_response = SimulationResponse(**simulation.__dict__)
    risk_response = RiskAssessmentResponse(
        risk_score=risk.risk_score,
        risk_level=risk.risk_level,
        signals=[RiskSignalResponse(name=s.name, impact=s.impact) for s in risk.signals],
        model_is_demo_data=risk.model_is_demo_data,
        model_version=risk.model_version,
        model_confidence=risk.model_confidence,
        notes=risk.notes,
    )
    policy_response = PolicyEvaluationResponse(
        decision=policy_result.decision,
        matched_rules=[
            RuleOutcomeResponse(
                rule_name=o.rule_name,
                rule_type=o.rule_type.value if hasattr(o.rule_type, "value") else str(o.rule_type),
                decision=o.decision, reason=o.reason,
            )
            for o in policy_result.matched_rules
        ],
        unevaluated_rules=[
            RuleOutcomeResponse(
                rule_name=o.rule_name,
                rule_type=o.rule_type.value if hasattr(o.rule_type, "value") else str(o.rule_type),
                decision=o.decision, reason=o.reason,
            )
            for o in policy_result.unevaluated_rules
        ],
    )

    ai_result = None
    ai_response: AIAssessmentResponse | None = None
    ai_status = "skipped_no_api_key"
    if ai_service is not None:
        from ai_analyst.schemas import Evidence

        evidence = Evidence(
            transaction={
                "chain": request.chain, "from": request.from_address,
                "to": request.to, "value": request.value,
            },
            parsed=parsed_response.model_dump(mode="json"),
            simulation=simulation_response.model_dump(mode="json"),
            risk=risk_response.model_dump(mode="json"),
            policy=policy_response.model_dump(mode="json"),
        )
        ai_result = await ai_service.analyze(evidence)
        ai_response = AIAssessmentResponse(
            summary=ai_result.summary,
            risk_assessment=ai_result.risk_assessment,
            findings=ai_result.findings,
            potential_impact=ai_result.potential_impact,
            recommendation=ai_result.recommendation,
            confidence=ai_result.confidence,
            is_fallback=ai_result.is_fallback,
            notes=ai_result.notes,
        )
        ai_status = "complete"

    analysis_id = None
    persistence_status = "complete"
    try:
        persisted = await save_analysis(
            db,
            user_id=user_id,
            chain=request.chain,
            from_address=request.from_address,
            to_address=request.to,
            value_wei=request.value,
            data=request.data,
            parsed=parsed,
            simulation=simulation,
            risk=risk,
            policy_result=policy_result,
            ai_result=ai_result,
        )
        analysis_id = persisted.id
    except Exception:
        # A persistence failure must never hide a completed analysis from
        # the caller — log it and report it honestly, don't raise.
        logger.exception("failed to persist transaction analysis")
        persistence_status = "failed"

    return TransactionAnalyzeResponse(
        parsed=parsed_response,
        simulation=simulation_response,
        risk=risk_response,
        policy=policy_response,
        ai_assessment=ai_response,
        analysis_id=analysis_id,
        pipeline_status={
            "parser": "complete",
            "simulation": "complete",
            "ml_risk": "complete",
            "policy": "complete",
            "ai_analyst": ai_status,
            "persistence": persistence_status,
        },
    )
