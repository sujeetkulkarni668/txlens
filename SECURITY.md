# Security Policy

TxLens is a security-analysis tool. Please report vulnerabilities responsibly.

## Reporting a vulnerability

Do **not** open a public GitHub issue for security vulnerabilities. Instead,
email the maintainers at:

**`security@txlens.example`** — **this is a placeholder domain, not a real,
monitored inbox.** No actual organization maintains this project's security
reporting infrastructure yet. Replace this with a real, monitored address
before any real-world deployment or public release; until then, do not
assume reports sent here reach anyone.

A report should include:

- A description of the vulnerability and its impact
- Steps to reproduce
- Any relevant logs or proof-of-concept code

We aim to acknowledge reports within 5 business days.

## Scope and important limitations

- TxLens analyzes **public** on-chain information and simulated transaction
  outcomes. It does not have access to, and never requests, private keys or
  seed phrases.
- TxLens **cannot** arbitrarily block transactions on decentralized networks.
  Policy enforcement via smart contracts applies only to transactions routed
  through TxLens-controlled contracts (see `contracts/`).
- AI-generated output (risk explanations, recommendations) is advisory. It
  never gains elevated privileges and never triggers signing or fund
  movement on its own.
- Blockchain/contract content retrieved for AI analysis is treated as
  **untrusted data**, not instructions (prompt-injection resistance).
- Authentication (`app/auth/`) uses PBKDF2-HMAC-SHA256 password hashing
  and HS256-only JWTs, both implemented against the Python standard
  library rather than a third-party crypto library — reviewers should
  scrutinize this code path specifically rather than assume a
  well-known library's guarantees apply.
- **Nothing in this repository has been security-audited or penetration
  tested.** It was built in an environment with no network access and no
  Docker/Foundry, so most of the security-relevant code
  (authentication, rate limiting, the Solidity contract) has never
  actually been run, let alone audited — see the root README's
  Limitations section for exactly what has and hasn't been executed.
  Treat every claim in this file as a design intent, not a verified
  guarantee, until independently confirmed.

## Known gaps to be aware of before any real deployment

- No email verification, password reset, or session/token revocation.
- `TxLensPolicyVault` has no privileged pause/admin mechanism — a bug
  found post-deployment has no on-chain emergency lever.
- The frontend does not yet attach authentication tokens to its backend
  requests (see CONTRIBUTING.md "Good first issues").
- `get_current_user_id`'s JWT verification, the rate limiter, and the
  password/JWT modules have unit tests but have never been exercised
  through an actual running HTTP server.

## Supported versions

This is a pre-1.0 prototype. Only the `main` branch is supported.
