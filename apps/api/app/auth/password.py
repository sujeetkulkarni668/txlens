"""Password hashing using stdlib PBKDF2-HMAC-SHA256 (no bcrypt/passlib
dependency needed — this is a legitimate, currently-recommended KDF, not
a shortcut: OWASP's 2023 password-storage guidance lists PBKDF2-SHA256
with >=600,000 iterations as an acceptable choice). Deliberately kept
dependency-free so it's testable without installing anything, matching
the pattern used elsewhere in this codebase (urllib instead of httpx,
hand-rolled ABI decoding instead of eth-abi).

Stored format: "pbkdf2_sha256${iterations}${salt_b64}${hash_b64}" — the
iteration count is embedded so it can be increased later without
invalidating existing hashes (a new verification just uses whatever
count is stored, and callers can re-hash on successful login if the
count is below the current default).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_ALGORITHM_TAG = "pbkdf2_sha256"
_DEFAULT_ITERATIONS = 600_000
_SALT_BYTES = 16


class InvalidHashFormatError(ValueError):
    pass


def hash_password(password: str, *, iterations: int = _DEFAULT_ITERATIONS) -> str:
    if not password:
        raise ValueError("password must not be empty")
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join(
        [
            _ALGORITHM_TAG,
            str(iterations),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(derived).decode("ascii"),
        ]
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Timing-safe comparison. Returns False (never raises) for a
    malformed stored hash — a corrupt/foreign hash should fail closed,
    not error out the login endpoint."""
    try:
        algorithm, iterations_str, salt_b64, hash_b64 = stored_hash.split("$")
        if algorithm != _ALGORITHM_TAG:
            return False
        iterations = int(iterations_str)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(hash_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def needs_rehash(stored_hash: str, *, target_iterations: int = _DEFAULT_ITERATIONS) -> bool:
    """True if a hash was created with fewer iterations than the current
    default — callers should re-hash (with the plaintext password they
    just verified) and update storage when this is True."""
    try:
        algorithm, iterations_str, _, _ = stored_hash.split("$")
    except ValueError:
        return True
    if algorithm != _ALGORITHM_TAG:
        return True
    return int(iterations_str) < target_iterations
