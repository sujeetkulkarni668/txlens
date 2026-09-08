# Integration tests

`test_full_pipeline.py` — real, executed end-to-end tests composing
Parser → Simulation → ML risk → Policy → AI Analyst exactly the way
`apps/api/app/api/v1/endpoints/transactions.py` wires them, using a
`FakeBlockchainProvider` and a scripted `FakeAIProvider` so this runs
with zero network access. Three scenarios: a boring low-risk transfer, a
high-risk unlimited-approval-to-a-new-contract case where every stage
independently escalates and agrees, and a worst-case "infra is degraded"
case (no trace support + unparseable AI output) proving the pipeline
degrades to a safe `REVIEW`/`is_fallback` state rather than raising or
silently looking like a clean pass.

Run from the repo root:

```bash
PYTHONPATH=apps/api:services/risk-engine:services/ai-analyst:. \
  python3 -m unittest discover -s tests/integration -v
```

**What this does and doesn't cover**: this proves the seams between the
independently-tested components (each already covered by its own unit
tests) actually compose correctly end-to-end. It does **not** cover the
HTTP layer, the database, or a real RPC/LLM connection — those remain
syntax-checked only (DB/HTTP) or genuinely unverified (a real RPC node's
`debug_traceCall` behavior, the live Anthropic API) — see the root
README's Limitations section.

`test_e2e.py` (frontend → running backend, per product spec section 27)
is not implemented — it needs an actual running stack (Postgres, the
API, and a browser or headless equivalent), none of which are available
in the environment that generated this repo.
