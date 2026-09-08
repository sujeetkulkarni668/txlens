"""RiskEngineService — the integration point between the parser/simulation
outputs (Phases 2-3) and the ML model (this phase).

`assess_from_pipeline` builds a RiskFeatures instance from what's already
known at analyze-time (parsed transaction + simulation result) plus
optional externally-supplied wallet/contract stats. Whatever isn't
supplied is left as None and imputed downstream — never guessed at here.
"""
from __future__ import annotations

from ml.features.schema import RiskFeatures
from risk_engine.model import RiskModel
from risk_engine.schemas import RiskAssessment


class RiskEngineService:
    def __init__(self, model: RiskModel):
        self._model = model

    def assess(self, features: RiskFeatures) -> RiskAssessment:
        return self._model.predict(features)

    def assess_from_pipeline(
        self,
        *,
        transaction_type: str,
        transaction_value_native: float,
        simulation_warning_count: int,
        approval_ratio_to_max: float = 0.0,
        is_unlimited_approval: bool = False,
        wallet_age_days: float | None = None,
        wallet_transaction_frequency: float | None = None,
        wallet_unique_contract_count: float | None = None,
        wallet_unique_token_count: float | None = None,
        wallet_recent_activity: float | None = None,
        wallet_contract_interaction_frequency: float | None = None,
        value_deviation: float | None = None,
        contract_age_days: float | None = None,
    ) -> RiskAssessment:
        features = RiskFeatures(
            wallet_age=wallet_age_days,
            transaction_frequency=wallet_transaction_frequency,
            transaction_value=transaction_value_native,
            value_deviation=value_deviation,
            contract_age=contract_age_days,
            approval_ratio_to_max=approval_ratio_to_max,
            is_unlimited_approval=is_unlimited_approval,
            unique_contract_count=wallet_unique_contract_count,
            unique_token_count=wallet_unique_token_count,
            recent_activity=wallet_recent_activity,
            contract_interaction_frequency=wallet_contract_interaction_frequency,
            simulation_warning_count=simulation_warning_count,
            transaction_type=transaction_type,
        )
        return self._model.predict(features)
