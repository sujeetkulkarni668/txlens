# ml

Risk-model training pipeline (product spec section 14). **Not implemented
yet — scaffolded in Phase 4.**

- `training/` — reproducible training scripts
- `features/` — feature extraction (wallet age, tx frequency/value,
  approval amount, unlimited-approval flag, contract age, etc.)
- `models/` — serialized model artifacts (gitignored except `.gitkeep`)
- `inference/` — inference wrapper consumed by services/risk-engine

Any model trained on synthetic/demo data must be labeled as such in its
metadata and surfaced to end users via the API response — never presented as
production-accuracy.
