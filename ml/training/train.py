"""Reproducible training pipeline for the Phase 4 risk model.

Trains an interpretable model (LogisticRegression) on the synthetic
dataset from generate_synthetic_dataset.py, evaluates it on a held-out
split, and serializes the fitted scaler + model + metadata to ml/models/.

Run: PYTHONPATH=<repo root> python3 ml/training/train.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ml.features.schema import FEATURE_NAMES
from ml.training.generate_synthetic_dataset import generate_dataset

MODEL_VERSION = "risk-model-v1-synthetic"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def train(n_samples: int = 4000, seed: int = 42) -> dict:
    X, y = generate_dataset(n_samples=n_samples, seed=seed)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(
        max_iter=1000, class_weight="balanced", random_state=seed
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", zero_division=0
    )
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "positive_rate": float(y.mean()),
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler, "feature_names": FEATURE_NAMES}, MODELS_DIR / "risk_model.joblib")

    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "trained_on": "synthetic",
        "is_demo_data": True,
        "model_type": "LogisticRegression",
        "feature_names": FEATURE_NAMES,
        "metrics": metrics,
        "notes": [
            "Trained entirely on synthetic, rule-labeled data — see "
            "ml/training/generate_synthetic_dataset.py for the labeling "
            "logic. Metrics above describe fit to that synthetic prior, "
            "not real-world detection accuracy.",
        ],
    }
    (MODELS_DIR / "risk_model_metadata.json").write_text(json.dumps(metadata, indent=2))

    return metadata


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, indent=2))
