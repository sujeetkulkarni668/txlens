"""Synthetic training data generator for the Phase 4 risk model.

IMPORTANT: this data is synthetic/demo, not observed on-chain behavior.
The rule-based labeling function below encodes a reasonable, documented
prior about what correlates with risk (unlimited approvals, brand-new
counterparty contracts, unusually large/deviant transaction values, thin
wallet history) — it is not derived from real incident data. Every
consumer of the trained model must be told this (see
services/risk-engine and app/models/risk.py's `model_is_demo_data` field).
Replace this generator with a real labeled dataset before relying on the
model for anything beyond a demo.
"""
from __future__ import annotations

import random

import numpy as np

from ml.features.schema import TRANSACTION_TYPE_ORDER, RiskFeatures, to_vector

MAX_UINT256 = 2**256 - 1


def _sample_one(rng: random.Random) -> tuple[RiskFeatures, int]:
    tx_type = rng.choices(
        TRANSACTION_TYPE_ORDER, weights=[0.35, 0.30, 0.20, 0.13, 0.02], k=1
    )[0]

    wallet_age = rng.uniform(0, 900)
    transaction_frequency = rng.uniform(0, 20)
    transaction_value = rng.expovariate(1 / 0.5)  # ETH, skewed toward small
    value_deviation = rng.gauss(0, 1.5)
    contract_age = rng.uniform(0, 900) if tx_type in ("erc20_approval", "erc20_transfer", "contract_interaction") else None
    unique_contract_count = rng.uniform(0, 60)
    unique_token_count = rng.uniform(0, 30)
    recent_activity = rng.uniform(0, 40)
    contract_interaction_frequency = rng.uniform(0, 1)
    simulation_warning_count = rng.choices([0, 1, 2, 3], weights=[0.6, 0.2, 0.15, 0.05])[0]

    is_unlimited_approval = False
    approval_ratio = 0.0
    if tx_type == "erc20_approval":
        is_unlimited_approval = rng.random() < 0.35
        approval_ratio = 1.0 if is_unlimited_approval else rng.uniform(0, 0.4)

    features = RiskFeatures(
        wallet_age=wallet_age,
        transaction_frequency=transaction_frequency,
        transaction_value=transaction_value,
        value_deviation=value_deviation,
        contract_age=contract_age,
        approval_ratio_to_max=approval_ratio,
        is_unlimited_approval=is_unlimited_approval,
        unique_contract_count=unique_contract_count,
        unique_token_count=unique_token_count,
        recent_activity=recent_activity,
        contract_interaction_frequency=contract_interaction_frequency,
        simulation_warning_count=simulation_warning_count,
        transaction_type=tx_type,
    )

    # Rule-based synthetic label — a documented prior, not ground truth.
    risk_signal = 0.0
    risk_signal += 3.0 if is_unlimited_approval else 0.0
    risk_signal += 2.0 if (contract_age is not None and contract_age < 14) else 0.0
    risk_signal += 1.5 if wallet_age < 7 else 0.0
    risk_signal += 1.0 if abs(value_deviation) > 2.5 else 0.0
    risk_signal += 0.6 * simulation_warning_count
    risk_signal += 1.2 if (unique_contract_count < 2 and tx_type == "contract_interaction") else 0.0
    risk_signal -= 0.8 if wallet_age > 365 else 0.0
    risk_signal -= 0.5 if (contract_age is not None and contract_age > 365) else 0.0
    risk_signal += rng.gauss(0, 0.6)  # noise, so the boundary isn't a clean rule

    label = 1 if risk_signal > 2.0 else 0
    return features, label


def generate_dataset(n_samples: int = 4000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Returns (X, y) — X is an (n_samples, n_features) float array built
    via `to_vector`, y is a {0,1} risky/not-risky label array."""
    rng = random.Random(seed)
    rows = []
    labels = []
    for _ in range(n_samples):
        features, label = _sample_one(rng)
        rows.append(to_vector(features))
        labels.append(label)
    return np.vstack(rows), np.array(labels, dtype=np.int64)


if __name__ == "__main__":
    X, y = generate_dataset()
    print(f"generated {len(y)} samples, positive rate = {y.mean():.3f}")
