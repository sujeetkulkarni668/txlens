# Contributing to TxLens

TxLens is an open-source pre-transaction blockchain security prototype.
All 12 planned phases (see `docs/roadmap.md`) have landed — parsing,
simulation, ML risk scoring, policy evaluation, an AI analyst, an MCP
server, a Solidity policy contract, a frontend, DB persistence, and
security hardening are all implemented. That does **not** mean
everything has been *run*: this project was built with no network access
and no Docker/Foundry, so verification depth varies by component (162
executed Python tests; the frontend is type-checked only; the Solidity
contract has never been compiled at all). See the root
[`README.md`](README.md) Limitations section before assuming any
particular piece works — read it before opening an issue reporting
something "broken" that may simply be unverified.

## Development principles

- Every technology used must have a legitimate, explainable purpose (see
  `README.md#architecture`).
- Never fabricate results: unsupported capabilities must return an explicit
  "unsupported"/"unknown" state rather than a fake success.
- Keep services simple and modular; avoid speculative abstractions.
- All sensitive operations (policy mutation, MCP privileged tools) require
  explicit authorization — never implicit or automatic.

## Workflow

1. Fork and branch from `main`.
2. Run the relevant local validation for the area you're changing (see
   `README.md#local-setup` and `README.md#testing`).
3. Keep PRs scoped to a single concern.
4. Include or update tests for any behavioral change.
5. Do not commit secrets, `.env` files, or real RPC/API keys.

## Code style

- Backend (Python): type hints required, formatted/linted per CI config.
- Frontend (TypeScript): strict mode, formatted/linted per CI config.
- Solidity: NatSpec on public/external functions, Foundry tests required for
  new contract logic.

## Good first issues

Things known to need attention, in rough priority order:

1. **Frontend auth wiring** — the frontend predates real authentication
   and doesn't call `/auth/login` or attach a bearer token; its API
   calls will 401 against a real backend. See README Limitations.
2. **Compile and fix the Solidity contract** — `contracts/` has never
   been run through `solc`/`forge` at all. Start here:
   `forge install foundry-rs/forge-std --no-commit && forge build`.
3. **Actually run this against a real database** — no SQLAlchemy code
   in this repo has ever executed; expect the first real run to surface
   issues (`app/persistence/`, the DB session setup, and the Alembic
   migration all need generating/testing for real).
4. **Simplify the multi-service `PYTHONPATH`** — `apps/api` importing
   `ml/`, `services/risk-engine/`, and `services/ai-analyst/` directly
   via `PYTHONPATH` (see docker/api.Dockerfile) is a known MVP
   simplification. A real internal API boundary (or proper Python
   packaging with `pip install -e`) would be cleaner.
5. **Wallet/contract/token intelligence** (product spec sections 11-13)
   — currently scoped to what raw RPC calls provide. Real history-based
   signals need an indexer/explorer integration.
