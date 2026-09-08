"""ML risk-model feature schema (product spec section 14).

Shared between the training pipeline (ml/training/) and the inference
service (services/risk-engine/) so the two can never silently drift out of
sync on feature order or semantics.

Several features require historical wallet/contract data that a plain EVM
JSON-RPC endpoint cannot cheaply provide (no indexer): wallet_age,
contract_age, unique_contract_count, unique_token_count, recent_activity,
contract_interaction_frequency, transaction_frequency, value_deviation.
Those are Optional here — when unavailable, `to_vector` imputes a neutral
value and reports it, rather than the caller silently getting a fabricated
number (product spec section 34).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Neutral (roughly "average, nothing notable") imputed values used only
# when a feature genuinely could not be computed. Chosen so imputation
# nudges the model toward "insufficient evidence to flag" rather than
# toward either extreme.
_IMPUTATION_DEFAULTS: dict[str, float] = {
    "wallet_age": 180.0,
    "transaction_frequency": 1.0,
    "value_deviation": 0.0,
    "contract_age": 180.0,
    "unique_contract_count": 5.0,
    "unique_token_count": 3.0,
    "recent_activity": 5.0,
    "contract_interaction_frequency": 0.3,
}

TRANSACTION_TYPE_ORDER = [
    "native_transfer",
    "erc20_transfer",
    "erc20_approval",
    "contract_interaction",
    "unknown",
]


@dataclass
class RiskFeatures:
    """One row of model input. All fields except the always-computable
    ones are Optional[float] — None means "not available", never "zero"."""

    # Wallet-history features — require an indexer; None if unavailable.
    wallet_age: float | None = None  # days since first observed tx
    transaction_frequency: float | None = None  # txs/day, recent window
    value_deviation: float | None = None  # z-score of this tx's value vs wallet history
    unique_contract_count: float | None = None
    unique_token_count: float | None = None
    recent_activity: float | None = None  # tx count, last 30 days
    contract_interaction_frequency: float | None = None  # 0..1

    # Contract-history features — require an indexer/explorer; None if
    # unavailable (e.g. counterparty is an EOA, or data wasn't fetched).
    contract_age: float | None = None  # days since deployment

    # Always computable from this transaction alone (Phase 2/3 output).
    transaction_value: float = 0.0  # native units (e.g. ETH), this tx
    approval_ratio_to_max: float = 0.0  # token_amount / 2**256-1, 0 if N/A
    is_unlimited_approval: bool = False
    simulation_warning_count: int = 0
    transaction_type: str = "unknown"  # one of TRANSACTION_TYPE_ORDER

    def known_feature_ratio(self) -> float:
        """Fraction of the optional, indexer-dependent features that are
        actually populated — used to scale down reported model confidence
        when evidence is thin."""
        optional_names = list(_IMPUTATION_DEFAULTS.keys())
        known = sum(1 for name in optional_names if getattr(self, name) is not None)
        return known / len(optional_names)

    def imputed_fields(self) -> list[str]:
        return [name for name in _IMPUTATION_DEFAULTS if getattr(self, name) is None]


FEATURE_NAMES: list[str] = [
    "wallet_age",
    "transaction_frequency",
    "transaction_value",
    "value_deviation",
    "contract_age",
    "approval_ratio_to_max",
    "is_unlimited_approval",
    "unique_contract_count",
    "unique_token_count",
    "recent_activity",
    "contract_interaction_frequency",
    "simulation_warning_count",
] + [f"tx_type_{t}" for t in TRANSACTION_TYPE_ORDER]


def to_vector(features: RiskFeatures) -> np.ndarray:
    """Convert a RiskFeatures instance into the fixed-order numeric vector
    the model consumes. Missing optional fields are imputed with a
    documented neutral default — call `features.imputed_fields()`
    separately to know which ones were.
    """
    values: list[float] = [
        features.wallet_age if features.wallet_age is not None else _IMPUTATION_DEFAULTS["wallet_age"],
        features.transaction_frequency
        if features.transaction_frequency is not None
        else _IMPUTATION_DEFAULTS["transaction_frequency"],
        features.transaction_value,
        features.value_deviation
        if features.value_deviation is not None
        else _IMPUTATION_DEFAULTS["value_deviation"],
        features.contract_age if features.contract_age is not None else _IMPUTATION_DEFAULTS["contract_age"],
        features.approval_ratio_to_max,
        1.0 if features.is_unlimited_approval else 0.0,
        features.unique_contract_count
        if features.unique_contract_count is not None
        else _IMPUTATION_DEFAULTS["unique_contract_count"],
        features.unique_token_count
        if features.unique_token_count is not None
        else _IMPUTATION_DEFAULTS["unique_token_count"],
        features.recent_activity
        if features.recent_activity is not None
        else _IMPUTATION_DEFAULTS["recent_activity"],
        features.contract_interaction_frequency
        if features.contract_interaction_frequency is not None
        else _IMPUTATION_DEFAULTS["contract_interaction_frequency"],
        float(features.simulation_warning_count),
    ]
    one_hot = [1.0 if features.transaction_type == t else 0.0 for t in TRANSACTION_TYPE_ORDER]
    return np.array(values + one_hot, dtype=np.float64)
