# contracts

`TxLensPolicyVault` — the on-chain policy/enforcement contract from
product spec section 19.

## What it does

Each account (not a single global owner) deposits into its own
sub-balance and configures its own policy inside this one shared
contract:

- `maximum transaction amount` — per-call cap (0 = unlimited)
- `daily spending limit` — rolling 1-day window, resets lazily on the
  next action after the window elapses (0 = unlimited)
- `approved recipients` — opt-in allowlist, enforced only if enabled
- `approved contracts` — opt-in allowlist for calls that carry calldata,
  enforced only if enabled

`executeAction` reverts (with a descriptive reason) rather than silently
no-opping when an action violates the caller's policy — that revert *is*
the "reject" behavior from the product spec. A policy must be explicitly
set (`setPolicy`) before `executeAction` will do anything at all; there
is no implicit "unlimited by default" state to fall into.

**This contract can only enforce policy on transactions routed through
it.** It cannot see, block, or influence anything a user signs directly
from their own EOA outside this contract — see the root
[`SECURITY.md`](../SECURITY.md).

## Design choices worth knowing

- **No privileged admin/owner role.** Every function is scoped to
  `msg.sender`'s own balance and policy. No single key can move another
  user's funds, and there's no upgrade/pause backdoor. Simpler and safer
  for an MVP than an `Ownable` pattern would be, at the cost of not
  having an emergency-pause lever — worth revisiting before mainnet use.
- **No `delegatecall`, anywhere.** A target contract called via
  `executeAction` can never take over the vault's storage.
- **Checks-effects-interactions + a `nonReentrant` guard** on both
  `withdraw` and `executeAction` — balance/dailySpent are debited before
  the external call, and the guard additionally blocks any reentrant call
  from succeeding even if that ordering were ever broken by a future
  change.
- **No signature/meta-transaction surface**, so there's no classic
  "replay a captured signature" vector — every action is authenticated by
  `msg.sender` directly. See the test file's `test_identical_repeated_...`
  test and its doc comment for what "replay" means (or rather, doesn't
  apply) here.
- **`executeAction` forwards `data` verbatim via a raw `.call`.** That's
  the point (executing an approved action on the user's behalf), but it
  means the amount/recipient/contract checks are the *only* protection
  against arbitrary calldata — enable `useApprovedContracts` for any real
  dApp interaction, not just the spend limits.

## What's actually been verified

**Nothing, at the Solidity level.** No `solc` or `forge` were available
in the environment that generated this repo (no network access, no
Docker) — `TxLensPolicyVault.sol`, the Foundry tests, and the deploy
script have not been compiled, let alone run. This is a materially
different (weaker) verification status than the rest of this
repository: the Python services in `apps/` and `services/` at least have
real, executed, passing tests; this directory has none. Treat it as an
unverified draft.

## Validate for real

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
cd contracts
forge install foundry-rs/forge-std --no-commit
forge build
forge test -vvv
```

25 tests exist in `test/TxLensPolicyVault.t.sol` covering: deposits/
withdrawals, the policy-must-be-set gate, max-transaction-amount
(under/at/over the limit, and the 0-means-unlimited convention), daily
spend limit (blocking, window reset, the reset-aware view function),
approved recipients, approved contracts (including that a plain value
transfer isn't gated by the contract allowlist), zero-address rejection,
insufficient-balance rejection, cross-user isolation (Alice can't touch
Bob's balance or be constrained by Bob's policy), reentrancy (a
`ReentrantWithdrawAttacker` mock proving the second, reentrant withdrawal
attempt reverts), and a failed external call rolling back the vault's
internal accounting rather than debiting a user for an action that
didn't actually happen.
