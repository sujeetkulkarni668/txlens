"""Loads the trained risk model and turns a RiskFeatures instance into a
RiskAssessment (product spec section 14).

Model choice: LogisticRegression over standardized features. This is
"interpretable" in a concrete, checkable sense — each feature's
contribution to the prediction is exactly `coefficient * standardized_value`,
computable without any additional explainability library (no SHAP
installed). Contributions are reported as `signals`, scaled by a fixed
readability factor; they are relative contribution magnitudes, not a
promise that they sum exactly to `risk_score` (that would only hold in
probability space very close to a 50% decision boundary, since the
sigmoid is nonlinear).
"""
from __future__ import annotations

from pathlib import Path

import joblib

from ml.features.schema import FEATURE_NAMES, RiskFeatures, to_vector
from risk_engine.schemas import RiskAssessment, RiskSignal

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "models" / "risk_model.joblib"

_SIGNAL_SCALE = 10  # readability factor only — see module docstring
_TOP_N_SIGNALS = 6

_LEVEL_THRESHOLDS = (  # (max_score_inclusive, level)
    (24, "LOW"),
    (49, "MEDIUM"),
    (74, "HIGH"),
    (100, "CRITICAL"),
)


def _risk_level(score: int) -> str:
    for max_score, level in _LEVEL_THRESHOLDS:
        if score <= max_score:
            return level
    return "CRITICAL"  # unreachable given the table ends at 100, kept for safety


class RiskModel:
    def __init__(self, model, scaler, feature_names: list[str], model_version: str = "unknown"):
        if feature_names != FEATURE_NAMES:
            raise ValueError(
                "loaded model's feature_names do not match the current "
                "ml.features.schema.FEATURE_NAMES — the model is stale "
                "relative to the feature schema and must be retrained"
            )
        self._model = model
        self._scaler = scaler
        self._feature_names = feature_names
        self._model_version = model_version

    @classmethod
    def load(cls, path: Path = DEFAULT_MODEL_PATH, model_version: str = "unknown") -> "RiskModel":
        if not path.exists():
            raise FileNotFoundError(
                f"no trained model at {path} — run `PYTHONPATH=. python3 "
                "ml/training/train.py` first"
            )
        bundle = joblib.load(path)
        return cls(
            model=bundle["model"],
            scaler=bundle["scaler"],
            feature_names=bundle["feature_names"],
            model_version=model_version,
        )

    def predict(self, features: RiskFeatures) -> RiskAssessment:
        vector = to_vector(features).reshape(1, -1)
        scaled = self._scaler.transform(vector)

        probability = float(self._model.predict_proba(scaled)[0, 1])
        risk_score = int(round(probability * 100))
        risk_score = max(0, min(100, risk_score))

        contributions = self._model.coef_[0] * scaled[0]
        ranked = sorted(
            zip(self._feature_names, contributions), key=lambda pair: -abs(pair[1])
        )[:_TOP_N_SIGNALS]
        signals = [
            RiskSignal(name=name, impact=int(round(contribution * _SIGNAL_SCALE)))
            for name, contribution in ranked
            if round(contribution * _SIGNAL_SCALE) != 0
        ]

        notes: list[str] = []
        imputed = features.imputed_fields()
        confidence = features.known_feature_ratio()
        # known_feature_ratio only covers the indexer-dependent features;
        # floor it so a transaction with zero of them isn't reported as
        # literally 0% confidence (the always-computable features still
        # carry real signal).
        confidence = 0.35 + confidence * 0.65
        if imputed:
            notes.append(
                f"{len(imputed)} feature(s) unavailable and imputed with a neutral "
                f"default (requires wallet/contract history data this phase doesn't "
                f"fetch): {', '.join(imputed)}. Model confidence reduced accordingly."
            )

        return RiskAssessment(
            risk_score=risk_score,
            risk_level=_risk_level(risk_score),
            signals=signals,
            model_is_demo_data=True,
            model_version=self._model_version,
            model_confidence=round(confidence, 2),
            notes=notes,
        )
