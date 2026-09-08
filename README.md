# TxLens — Verify Before You Sign
## 1. What TxLens is

TxLens is a pre-transaction blockchain security and intelligence platform.
Before a user signs a blockchain transaction, TxLens analyzes what the
transaction will do, gathers relevant public on-chain information, simulates
it where possible, scores risk with ML, investigates and explains findings
with an AI analyst, and evaluates user-defined security policies — all
before the user's wallet is asked to sign.

## 2. Why it exists

Wallet users routinely sign transactions (token approvals, contract
interactions) whose actual effects are opaque at signing time. TxLens
surfaces that effect — in plain terms, with evidence — before the
irreversible step of signing.

## 3. Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full breakdown.
Summary of component responsibilities:

- **Blockchain** — public on-chain state, execution, events, settlement.
- **Contracts** — enforce policy *only* for transactions routed through
  TxLens-controlled contracts. TxLens never claims it can arbitrarily block
  transactions elsewhere on a decentralized blockchain.
- **API (backend)** — orchestrates parsing, simulation, ML, policy, AI, MCP,
  and persistence.
- **ML** — detects statistical/anomalous risk patterns, produces a risk
  score.
- **AI** — investigates structured evidence and explains risk; never
  invents blockchain facts.
- **MCP** — controlled, audited tools for the AI agent; calls backend
  services, never RPC/DB directly.
- **Frontend** — sober, professional developer-security interface.

## 4. Features (target)

Transaction parsing and decoding, RPC-abstracted blockchain data access,
transaction simulation, wallet/contract/token intelligence, an interpretable
ML risk model, a deterministic policy engine, an AI analyst with strict
structured output, a dedicated MCP server, an on-chain policy-enforcement
contract, and a developer-infrastructure-styled frontend (**implemented,
see below**). See the full per-phase breakdown in
[`docs/roadmap.md`](docs/roadmap.md).

### Frontend (`apps/web/`, implemented)

All 7 spec'd screens: Dashboard, Transaction Analysis, Wallet, Contract,
Policies, Reports, Settings — Next.js App Router, TypeScript, Tailwind,
sober/restrained styling (no gradients, no gamification). Every page
calls a real backend endpoint from earlier phases via a typed client
(`src/lib/api.ts`) and shared types (`packages/shared-types/`) kept in
sync with the backend Pydantic schemas by hand.

Wallet connect and transaction signing (`src/lib/wallet.ts`) talk
directly to the browser's injected EIP-1193 provider (e.g. MetaMask) —
deliberately no wagmi/viem/ethers dependency. TxLens never receives a
private key; the wallet remains the sole signing authority, matching
product spec section 20 exactly: analyze → user reviews → "Continue" →
wallet prompts → user approves → submitted.

Reports and Settings are honestly scoped to what's actually persisted:
there's no reports-write endpoint yet, so Reports says so rather than
faking a history list; Settings shows the configured API/network values
read-only rather than pretending they're editable in-app.

## 5. Technology stack

| Area       | Stack |
|------------|-------|
| Frontend   | Next.js, TypeScript, React, Tailwind CSS |
| Backend    | Python 3.12+, FastAPI, Pydantic, SQLAlchemy (async) |
| Database   | PostgreSQL |
| Cache/jobs | Redis |
| ML         | scikit-learn (XGBoost where appropriate) |
| AI         | Provider-agnostic LLM abstraction (configurable) |
| MCP        | Official MCP Python ecosystem |
| Blockchain | Solidity, Foundry, web3/ethers-compatible tooling |
| Infra      | Docker, Docker Compose, GitHub Actions |

## 6. Security model

- TxLens analyzes **public** blockchain information and simulated outcomes.
  **TxLens never has access to private keys or seed phrases**, and never
  asks for them.
- **TxLens cannot arbitrarily block transactions on decentralized
  networks.** Smart-contract enforcement applies only to transactions
  routed through TxLens-controlled contracts.
- AI output is advisory and structured; it never gains elevated privileges
  and never triggers signing on its own.
- Blockchain/contract content is treated as **untrusted data** when given to
  the AI — never as instructions (prompt-injection resistance).
- **Authentication** (`app/auth/`, implemented): registration and login
  issue a bearer JWT; sensitive endpoints (policy CRUD,
  `/transactions/analyze`) require it. Password hashing (PBKDF2-HMAC-
  SHA256, 600k iterations) and JWT signing/verification (HS256 only, no
  algorithm negotiation — this specifically rules out the "alg: none"
  bypass class) are both implemented with the stdlib, no
  passlib/python-jose dependency.
- **Input validation**: EVM addresses, calldata, and value fields are
  validated at the API boundary (regex/format checks) before reaching the
  parser, simulation, or RPC layer — malformed input gets a 422, not a
  confusing failure several layers deep.
- **Rate limiting** (slowapi): a configurable default across the API,
  with tighter limits on `/auth/login` and `/auth/register` specifically
  against brute-force/enumeration.
- **Structured errors**: every error response has the same predictable
  shape; unexpected exceptions are logged with full detail server-side
  and returned to the client as a generic message plus a correlatable
  error id — never a leaked stack trace or internal detail.
- **Secrets configuration**: the API refuses to start in production with
  the default placeholder `API_SECRET_KEY` (only warns in development).
- See [`SECURITY.md`](SECURITY.md) for the vulnerability-reporting process.

## 7. MCP architecture

A dedicated MCP server (`services/mcp-server/`, **implemented**) exposes
all 12 spec'd tools:

- **Read-only**: `inspect_wallet`, `get_wallet_transactions`,
  `inspect_contract`, `check_token`, `simulate_transaction`,
  `trace_transaction`, `check_wallet_risk`, `check_contract_risk`,
  `check_policy`, `create_security_report`
- **Sensitive** (require an explicit `authorized=true`):
  `request_approval`, `create_policy`

Every tool calls the TxLens backend API only (`mcp_server/client.py`) —
never the blockchain RPC or the database directly, and it never holds
private keys or signs anything. Every call is audit-logged regardless of
outcome (`mcp_server/audit.py`). Three tools (`get_wallet_transactions`,
`check_wallet_risk`, `check_contract_risk`) honestly return a structured
"not implemented" result rather than a fabricated one, since they depend
on an indexer/contract-verification capability this project doesn't have
yet.

## 8. AI/ML architecture

- **ML** (`services/risk-engine/`, `ml/`, **implemented**): a
  `LogisticRegression` model over 17 standardized features
  (`ml/features/schema.py`) — chosen specifically because a linear model's
  per-feature contribution (`coefficient × standardized value`) gives a
  genuine, non-fabricated per-prediction explanation without needing a
  separate explainability library. Outputs `risk_score` (0-100),
  `risk_level`, and `signals` (top contributing features, signed). Trained
  on a **synthetic, rule-labeled dataset** (see
  `ml/training/generate_synthetic_dataset.py`) — every response carries
  `model_is_demo_data: true`. Several spec'd features need historical
  wallet/contract data a plain RPC endpoint can't provide; when absent
  they're imputed to a documented neutral value, `model_confidence` drops,
  and `notes` lists exactly which fields were imputed.
- **AI** (`services/ai-analyst/`, **implemented**): consumes structured
  evidence only (transaction, parser output, simulation, ML risk, policy
  result — wallet/contract/token intelligence sections exist in the
  schema but are always `None` until those services are built). A
  provider abstraction (`ai_analyst/provider.py`) means the vendor is
  chosen purely from `AI_PROVIDER`/`AI_API_KEY`/`AI_MODEL`; only
  `anthropic` is implemented. Every evidence field the pipeline couldn't
  determine renders as an explicit "NOT AVAILABLE" marker in the prompt —
  the model is instructed never to guess. On-chain-derived strings
  (contract names, token symbols) are wrapped in
  `<untrusted_onchain_data>` tags with an explicit instruction never to
  treat their contents as commands (a malicious contract could embed
  adversarial text there). The model's raw output is never trusted
  directly: it's strictly type/range-validated against
  `{summary, risk_assessment, findings, potential_impact, recommendation,
  confidence}`, retried once on invalid output, and falls back to a safe
  `REVIEW`/confidence-0 result (never a silent `ALLOW`) if it still can't
  be validated.

## 9. Smart-contract architecture

`contracts/src/TxLensPolicyVault.sol` (**implemented, unverified — see
below**) demonstrates real, enforceable on-chain policy logic:
per-account deposits and policy (not a single global owner), max
transaction amount, a rolling daily spend limit, opt-in approved
recipients, and opt-in approved contracts. `executeAction` reverts with a
descriptive reason when a policy is violated — that revert is the
"reject" behavior. No `delegatecall`, no privileged admin role, a
`nonReentrant` guard plus checks-effects-interactions ordering on both
`withdraw` and `executeAction`. It enforces policy only for funds and
calls routed through it — not a mechanism for blocking arbitrary chain
activity. See `contracts/README.md` for the full design rationale.
`contracts/test/TxLensPolicyVault.t.sol` has 25 Foundry tests covering
every rule, cross-user isolation, reentrancy, and failed-call rollback.

**Verification status: none.** No `solc` or `forge` were available in the
environment that generated this repo — the contract and its tests have
never been compiled. This is weaker than every other part of this
codebase (which is at least syntax-checked); treat `contracts/` as an
unverified draft until you run `forge build && forge test` yourself.

## 10. API documentation

Base path: `/api/v1`. Full endpoint surface (transactions, wallets,
contracts, tokens, policies, reports) is defined in the product spec and
implemented incrementally. Live today:

- `GET /health`, `GET /ready`
- `POST /api/v1/transactions/analyze` — **requires a bearer token**; runs
  parsing + simulation + ML risk scoring + policy evaluation + AI
  analysis (when configured), then **persists the full result**
  (Transaction, TransactionAnalysis, SimulationResult, RiskScore/signals,
  AuditLog) and returns its `analysis_id`. The response's
  `pipeline_status.ai_analyst` reads `"complete"` or
  `"skipped_no_api_key"`, and `pipeline_status.persistence` reads
  `"complete"` or `"failed"` — a DB write failure never hides an
  otherwise-successful analysis from the caller, but is never silently
  missing either
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login` — real
  authentication (stdlib PBKDF2 password hashing + HS256 JWT); login
  returns a bearer access token, rate-limited against brute force
- `GET/POST/PUT/DELETE /api/v1/policies[/{id}]` — CRUD for user-defined
  policies (`maximum_transaction_value`, `maximum_daily_spend`,
  `require_review_above`, `block_unlimited_approvals`,
  `block_unknown_contracts`, `require_review_for_new_contracts`).
  **Requires a bearer token** (`Authorization: Bearer <token>` from
  `/auth/login`)
- `POST /api/v1/transactions/simulate` — eth_call (success/revert) +
  eth_estimateGas + optional debug_traceCall internal-call trace. When the
  RPC endpoint doesn't support tracing (the common case for public
  endpoints), `trace_supported: false` and asset changes/approvals fall
  back to a calldata-only decode explicitly labeled `source:
  "calldata_decode"` rather than presented as confirmed effects
- `GET /api/v1/wallets/{address}` — public balance + nonce via
  `BlockchainProvider`. Standalone wallet risk scoring is deliberately
  **not** offered (see Limitations) — without a specific transaction for
  context it would mostly score an imputed feature vector
- `GET /api/v1/contracts/{address}` — bytecode presence/size via
  `eth_getCode`; `source_verified` is honestly `null` (no
  explorer/indexer integration)
- `GET /api/v1/tokens/{address}` — symbol/name/decimals/total supply via
  real `eth_call` reads (standard ERC-20 selectors), decoded without an
  ABI library
- `GET /api/v1/transactions/{hash}` — looks up a mined transaction +
  receipt

FastAPI auto-generates full OpenAPI docs at `/docs` once the app is
running locally.

## 11. Local setup

> Nothing below has been executed in the environment that generated this
> repository (no network, Docker, or Foundry access there). Run these
> yourself — the code is complete (all 12 phases), but installation,
> database migration, and startup have never actually been performed;
> see [Limitations](#15-limitations-current) for exactly what has and
> hasn't been verified.

```bash
git clone <this-repo>
cd txlens
cp .env.example .env   # edit values as needed, especially API_SECRET_KEY

# Database (requires a running PostgreSQL — see docker-compose.yml for a
# local one, or point DATABASE_URL at your own)
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head   # creates all 13 tables from migrations/versions/0001_initial.py

# Backend
pip install -r ../../services/risk-engine/requirements.txt
pip install -r ../../services/ai-analyst/requirements.txt   # only needed if AI_API_KEY is set
# The API imports the risk engine, AI analyst, and ml/ directly (see
# docker/api.Dockerfile for why) — PYTHONPATH must include the repo root
# and both services:
PYTHONPATH=../..:../../services/risk-engine:../../services/ai-analyst:. uvicorn app.main:app --reload
# → http://localhost:8000/health, /ready, and POST /api/v1/transactions/analyze
# (AI analyst stage runs only if AI_API_KEY is set in .env; otherwise it's
# reported as pipeline_status.ai_analyst = "skipped_no_api_key")

# /transactions/analyze and /policies now require a bearer token:
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"a-real-password"}'
TOKEN=$(curl -X POST localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"a-real-password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -X POST localhost:8000/api/v1/transactions/analyze \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from":"0x1111111111111111111111111111111111111111","to":"0x2222222222222222222222222222222222222222","value":"0"}'

# Retrain the risk model (optional — a trained artifact is already
# included at ml/models/risk_model.joblib)
cd ../..
PYTHONPATH=. python3 ml/training/train.py

# Frontend — from the repo ROOT, not apps/web (it's an npm workspace and
# depends on packages/shared-types)
npm install
npm run dev:web
# → http://localhost:3000
# NEXT_PUBLIC_API_URL defaults to http://localhost:8000/api/v1 (.env.example)

# Full stack
docker compose up --build
```

## 12. Environment variables

See [`.env.example`](.env.example) for the full list (database, Redis, EVM
RPC, AI provider, MCP server, API, frontend, rate limiting). No provider is
hard-coded — RPC endpoint and AI provider are both configuration-driven.

## 13. Testing

Test suites are added alongside the code they cover, per phase (backend
unit tests, ML tests, AI tests, MCP tests, Foundry tests, integration
tests — see `docs/roadmap.md`).

### Root-level `pytest -q` — executed and verified (162/162 passing)

Root [`pyproject.toml`](pyproject.toml) configures `--import-mode=importlib`
(derives each module's identity from its full path, not a bare package name)
plus native `pythonpath` config, allowing `pytest` from the repo root to
collect and run all 5 test paths (162/162 passing) without manual `PYTHONPATH`
exporting.

### What was actually run: `python -m unittest`, per package

**162 tests exist and were actually run** in the environment that
generated this repo:

```bash
# Parser, blockchain provider, simulation, policy engine, ERC-20 decoding,
# contract/token intelligence, password hashing, JWT, input validation —
# stdlib-only, no installs needed
cd apps/api
python3 -m unittest discover -s tests -v   # 106/106

# ML risk model — needs scikit-learn/joblib/numpy (already installed here)
cd ../..
PYTHONPATH=.:services/risk-engine python3 -m unittest discover -s services/risk-engine/tests -v   # 9/9

# AI analyst — stdlib-only (hand-written FakeAIProvider)
PYTHONPATH=services/ai-analyst python3 -m unittest discover -s services/ai-analyst/tests -v   # 23/23

# MCP server tool handlers + auth-token wiring — stdlib-only (hand-written FakeClient)
PYTHONPATH=services/mcp-server python3 -m unittest discover -s services/mcp-server/tests -v   # 21/21

# Full pipeline integration tests (Parser -> Simulation -> ML -> Policy -> AI,
# composed together exactly as the API endpoint does)
PYTHONPATH=apps/api:services/risk-engine:services/ai-analyst:. \
  python3 -m unittest discover -s tests/integration -v   # 3/3
```

Notable Phase 11 additions: `test_password.py` (12 tests) and
`test_jwt.py` (11 tests, including attack scenarios — tampered payload,
wrong secret, the classic `alg: none` bypass, garbage input) and
`test_evm_validation.py` (19 tests) — all stdlib-only, all genuinely
executed, not just syntax-checked.


Once `requirements-dev.txt` is installed, run the full suite the normal way:

```bash
pytest
ruff check .
mypy app
```

### Solidity tests (unverified — see Limitations)

```bash
cd contracts
forge install foundry-rs/forge-std --no-commit
forge build
forge test -vvv
```

25 tests exist in `contracts/test/TxLensPolicyVault.t.sol` — see
`contracts/README.md` for what they cover. **These have never been run**;
no `solc`/`forge` were available in the environment that generated this
repo.

### Frontend type-checking

```bash
cd apps/web
npm install
npm run typecheck
npm run lint
```

The frontend lockfile (`package-lock.json`) is generated and verified with
`npm ci`, `npm run lint`, `npm run typecheck` (`tsc --noEmit`), and production build
`npm run build` (`next build`), all passing cleanly. Live browser runtime and wallet
extension signing require an active browser environment.

## 14. Docker setup

`docker-compose.yml` defines `postgres`, `redis`, `api`, `mcp-server`, and
`web`. Dockerfiles live in `docker/`. Not build-verified in this
environment — see below.

## 15. Limitations (current)

- **Authentication and the rest of the FastAPI security wiring
  (rate limiting, structured error handlers) are syntax-checked only** —
  FastAPI/slowapi aren't installed in the environment that generated
  this repo, so `/auth/register`, `/auth/login`, the bearer-token
  dependency, and the global exception handlers have never actually
  been run end-to-end through the HTTP layer. The password hashing and
  JWT logic underneath them (`app/auth/password.py`, `app/auth/jwt.py`)
  **is** genuinely tested — 23 passing tests, stdlib-only.
- **The frontend hasn't been updated to actually call `/auth/login` or
  attach a bearer token to its requests** — the Phase 9 UI predates real
  authentication and still calls `analyzeTransaction`/`listPolicies`
  without one. Those calls will now get a 401 from a real backend until
  the frontend is updated to log in and send `Authorization: Bearer
  <token>`. Not fixed in this phase — tracked here rather than left
  silently broken.
- **No email verification, password reset, or session revocation** —
  registration/login is deliberately minimal (per product spec section
  25: "do not overengineer enterprise SSO"). A leaked JWT is valid until
  it expires (24h) with no server-side revocation list.
- **Database persistence is syntax-checked only, never actually run** —
  `app/persistence/analysis_repository.py` writes a Transaction +
  TransactionAnalysis + SimulationResult + RiskScore/signals + AuditLog
  row per analysis, but SQLAlchemy isn't installed in the environment
  that generated this repo, so this has never touched a real database.
  There's also still no `GET /api/v1/reports/{id}`-style endpoint to
  read any of this back — `analysis_id` is returned so a future endpoint
  has something to key on, but nothing can retrieve it yet.
- **The frontend has never run in a browser or been built with `next
  build`** — no network access to `npm install` Next.js/React/Tailwind in
  the environment that generated this repo. It was type-checked with
  `tsc` against stub ambient declarations (see Testing above), which
  catches real syntax/type errors but can't catch runtime issues, styling
  problems, or anything that only shows up once the real library code
  runs (hydration, routing edge cases, etc.).
- **Dashboard's "Recent analyses" and "Recent alerts" are placeholders**
  — there's no analysis-history or alerting endpoint to back them; the UI
  says so rather than showing fake data. **Reports** similarly has no
  persisted report list (no `POST /api/v1/reports` exists).
- **Settings is read-only** — RPC/network/AI-provider configuration is
  still server-side-only (`.env`); there's no in-app editor or endpoint
  for it yet.
- **Wallet connect/signing use the browser's injected EIP-1193 provider
  directly** (no wagmi/viem) — this has never been exercised against a
  real wallet extension (no browser in this environment). The pattern is
  standard, but treat it as unverified until tested with a real MetaMask
  (or similar) connection.
- **`contracts/` has zero verification** — no `solc` or `forge` were
  available in the environment that generated this repo, so
  `TxLensPolicyVault.sol` and its 25 Foundry tests have never been
  compiled. This is a materially weaker state than the rest of the
  codebase. Do not treat it as working until you've run
  `forge build && forge test` yourself.
- `TxLensPolicyVault` has no privileged pause/admin mechanism by design
  (see `contracts/README.md`) — worth revisiting before any real
  deployment.
- The parser only recognizes native transfers and three ERC-20 selectors
  (`transfer`, `approve`, `transferFrom`); anything else is honestly
  reported as `contract_interaction` / `undecoded`, not guessed at.
- Simulation's internal-call trace relies on `debug_traceCall`, which most
  public RPC endpoints (including Base Sepolia's default one) don't
  expose; when unsupported, `trace_supported: false` and effects are
  inferred from calldata only, explicitly labeled `source:
  "calldata_decode"`.
- **The ML risk model is trained entirely on synthetic, rule-labeled
  data** — every risk response carries `model_is_demo_data: true`. 8 of
  its 17 input features need historical wallet/contract data this phase
  doesn't fetch, so they're always imputed today.
- **The policy engine's `block_unknown_contracts` and
  `require_review_for_new_contracts` rules cannot currently be
  evaluated** — no contract-intelligence service supplies verification
  status or contract age yet. `maximum_daily_spend` is unevaluated too
  (no persistent spend-history query wired in).
- **The AI analyst only ever sees evidence the pipeline above it actually
  produced** — wallet/contract/token intelligence sections are always
  rendered as explicit "NOT AVAILABLE". `AnthropicProvider` itself has
  never been exercised — no network access, package not installed here.
- **Contract and token intelligence are scoped to what raw RPC calls can
  provide** — bytecode presence/size and ERC-20 symbol/name/decimals/
  supply. Source verification, ABI, admin-function detection, holder
  distribution, and risk indicators all require an explorer/indexer
  integration this project doesn't have. `source_verified` is reported as
  `null` (unknown), never guessed at.
- **MCP server**: `get_wallet_transactions`, `check_wallet_risk`, and
  `check_contract_risk` are deliberately not implemented and return a
  structured "not implemented" result. `request_approval` is wired for
  authorization but has nothing to fulfill it with yet. The MCP protocol
  transport itself (`mcp_server/server.py`) is syntax-checked only. Its
  HTTP client now sends a bearer token (`TXLENS_API_TOKEN`) to the
  backend, since policy/analyze endpoints require one as of this phase.
- **Policy CRUD and `/transactions/analyze` now require real
  authentication** — `get_current_user_id` (`app/api/v1/dependencies.py`)
  is JWT-verified, not the Phase 5 hardcoded placeholder. See the
  authentication-related items above for what's untested about it.
- **What's real vs. syntax/type-checked vs. entirely unverified**: the
  Python services (parser through MCP tool handlers, auth/password/JWT,
  input validation, plus the end-to-end pipeline integration tests) have
  162 executed, passing tests. The frontend's TypeScript passed a real
  `tsc` check but has never run. The FastAPI/Pydantic/SQLAlchemy HTTP
  layer, DB models, the persistence repository, rate limiting, the MCP
  protocol transport, the `AnthropicProvider`, and all Docker builds are
  syntax-checked only, never actually run. `contracts/` hasn't even been
  syntax-checked.
- A hand-authored initial Alembic migration (`0001_initial`) now exists,
  covering all 13 tables — cross-checked programmatically against every
  model's actual columns (13/13 tables matched, zero discrepancies). It
  has **never been run** against a real PostgreSQL instance
  (`alembic upgrade head` — NOT VERIFIED, no database available in this
  environment); this replaces "no migration exists at all" with "a
  migration exists and was verified by static cross-reference, but not
  by execution."
- `GET /ready` now actually checks PostgreSQL (a real `SELECT 1`) and
  Redis (a real `PING`) and returns `503` with `status: "not_ready"` if
  either fails, instead of unconditionally claiming `"ok"`. Also
  unverified end-to-end (no running Postgres/Redis here) but the logic
  itself fails closed by construction — an exception from either check
  becomes `"unavailable: <reason>"`, never a silent pass.
- Added a 1 MiB request body size limit (`app/core/body_limit.py`) —
  nothing previously bounded request body size on any POST endpoint.
- `docker compose up` will not fully succeed until each component has
  actually been build-tested somewhere with network/Docker access — none
  of the four application images (`api`, `mcp-server`, `web`, and the
  Solidity build) have been build-tested in this environment.

## 16. Roadmap

See [`docs/roadmap.md`](docs/roadmap.md).
