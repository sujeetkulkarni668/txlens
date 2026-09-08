"""Persists a completed /transactions/analyze run to the database
(product spec section 3's core flow ends with "Result is stored in
audit/history" — this is that step, which no earlier phase actually
wired up despite every model it needs existing since Phase 1).

NOT executed in the environment that generated this repo — SQLAlchemy
isn't installed here (no network). Syntax-checked only, same as the rest
of the FastAPI/SQLAlchemy layer. Field names are cross-checked by hand
against app/models/*.py.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.policy import Policy  # noqa: F401 — imported for type clarity in signature below
from app.models.risk import RiskScore, RiskSignal
from app.models.simulation_result import SimulationResult
from app.models.transaction import Transaction
from app.models.transaction_analysis import TransactionAnalysis
from app.parser.schemas import ParsedTransaction
from app.policy.schemas import PolicyEvaluationResult
from app.simulation.schemas import SimulationResult as SimulationResultData
from risk_engine.schemas import RiskAssessment

try:
    from ai_analyst.schemas import AIAssessment
except ImportError:  # AI analyst dependency isn't installed in every environment
    AIAssessment = None  # type: ignore[assignment,misc]


async def save_analysis(
    db: AsyncSession,
    *,
    user_id: str,
    chain: str,
    from_address: str,
    to_address: str | None,
    value_wei: str,
    data: str | None,
    parsed: ParsedTransaction,
    simulation: SimulationResultData,
    risk: RiskAssessment,
    policy_result: PolicyEvaluationResult,
    ai_result: "AIAssessment | None" = None,
) -> Transaction:
    """Writes Transaction + TransactionAnalysis + SimulationResult +
    RiskScore(+signals) + an AuditLog entry in one unit of work, and
    returns the persisted Transaction (its `.id` is what a future
    GET /reports/{id}-style endpoint would key on).

    This does NOT persist the policy evaluation itself (there's no
    dedicated policy_evaluations table in the current schema — only the
    Policy definitions themselves are persisted); the policy decision is
    captured in the audit log's metadata instead so it's not lost.
    """
    transaction = Transaction(
        chain=chain,
        from_address=from_address,
        to_address=to_address,
        value_wei=value_wei,
        data=data,
        tx_type=parsed.tx_type.value,
        submitted=False,
    )
    db.add(transaction)
    await db.flush()  # assigns transaction.id without committing yet

    analysis = TransactionAnalysis(
        transaction_id=transaction.id,
        decoded_function=parsed.decoded_function,
        decoded_params=parsed.parameters,
        ai_summary=ai_result.summary if ai_result else None,
        ai_risk_assessment=ai_result.risk_assessment if ai_result else None,
        ai_findings=ai_result.findings if ai_result else None,
        ai_potential_impact=ai_result.potential_impact if ai_result else None,
        ai_recommendation=ai_result.recommendation if ai_result else None,
        ai_confidence=ai_result.confidence if ai_result else None,
    )
    db.add(analysis)

    simulation_row = SimulationResult(
        transaction_id=transaction.id,
        success=simulation.success,
        gas_estimate=simulation.gas_estimate,
        decoded_actions=simulation.decoded_actions,
        asset_changes=simulation.asset_changes,
        approvals=simulation.approvals,
        events=simulation.events,
        warnings=simulation.warnings,
        trace_supported=simulation.trace_supported,
    )
    db.add(simulation_row)

    risk_row = RiskScore(
        transaction_id=transaction.id,
        risk_score=risk.risk_score,
        risk_level=risk.risk_level,
        model_is_demo_data=risk.model_is_demo_data,
        model_version=risk.model_version,
    )
    db.add(risk_row)
    await db.flush()  # assigns risk_row.id for the signal rows below

    for signal in risk.signals:
        db.add(RiskSignal(risk_score_id=risk_row.id, name=signal.name, impact=signal.impact))

    db.add(
        AuditLog(
            actor_user_id=user_id,
            action="transaction_analyzed",
            resource_type="transaction",
            resource_id=str(transaction.id),
            metadata_json={
                "policy_decision": policy_result.decision.value,
                "risk_level": risk.risk_level,
                "ai_recommendation": ai_result.recommendation if ai_result else None,
            },
        )
    )

    await db.commit()
    await db.refresh(transaction)
    return transaction
