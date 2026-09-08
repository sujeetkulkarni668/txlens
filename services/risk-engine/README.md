# risk-engine

ML risk scoring service (product spec section 14).

- Model: interpretable `LogisticRegression` over 17 standardized features
  (`ml/features/schema.py`) — chosen specifically because a linear model's
  per-feature contribution (`coefficient x standardized value`) gives a
  genuine, non-fabricated per-prediction explanation, unlike a black-box
  ensemble without a SHAP-style explainer installed.
- Training data: **synthetic, rule-labeled** (see
  `ml/training/generate_synthetic_dataset.py`) — this is a documented
  demo prior, not observed on-chain incident data. Every response from
  this service reports `model_is_demo_data: true` accordingly.
- Several spec'd features (`wallet_age`, `contract_age`,
  `unique_contract_count`, etc.) require historical/indexer data that a
  plain JSON-RPC endpoint can't cheaply provide. When not supplied, they
  are imputed to a documented neutral value and the response's
  `model_confidence` is reduced and `notes` lists which fields were
  imputed — never silently treated as "zero risk".

## Retraining

```bash
cd txlens
python -m venv .venv && source .venv/bin/activate
pip install -r services/risk-engine/requirements.txt
PYTHONPATH=. python3 ml/training/train.py
```

This was actually run in the environment that generated this repo (see
`ml/models/risk_model_metadata.json` for the resulting metrics) — unlike
most of this codebase, the model artifact shipped here is real and
loadable, not just syntax-checked.
