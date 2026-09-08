"""Minimal HS256 JWT encode/decode — stdlib only (hmac/hashlib/base64/json),
no PyJWT/python-jose dependency.

Deliberately narrow: HS256 only, no algorithm negotiation. This sidesteps
the classic "alg confusion" JWT vulnerability class entirely — there's no
`alg` field to spoof into `none` or an asymmetric algorithm, because
nothing here ever reads `alg` from the token to decide how to verify it;
the signature is always recomputed as HMAC-SHA256 and compared
timing-safely. If you need RS256/asymmetric tokens later, use a real
library — this is intentionally not a general-purpose JWT implementation.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

_HEADER = {"alg": "HS256", "typ": "JWT"}


class InvalidTokenError(ValueError):
    pass


class ExpiredTokenError(InvalidTokenError):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(signing_input: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()


def encode_jwt(claims: dict, secret: str, *, expires_in_seconds: int | None = None) -> str:
    payload = dict(claims)
    now = int(time.time())
    payload.setdefault("iat", now)
    if expires_in_seconds is not None:
        payload["exp"] = now + expires_in_seconds

    header_b64 = _b64url_encode(json.dumps(_HEADER, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature_b64 = _b64url_encode(_sign(signing_input, secret))
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_jwt(token: str, secret: str) -> dict:
    """Verifies signature and expiry, returns the claims dict. Raises
    InvalidTokenError (or its subclass ExpiredTokenError) rather than
    returning None/False, so a caller can't accidentally treat a bad
    token as "no user" instead of "reject the request"."""
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("token does not have three segments")
    header_b64, payload_b64, signature_b64 = parts

    try:
        header = json.loads(_b64url_decode(header_b64))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidTokenError(f"malformed header: {exc}") from exc
    if header.get("alg") != "HS256":
        raise InvalidTokenError(f"unsupported algorithm: {header.get('alg')!r}")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = _sign(signing_input, secret)
    try:
        actual_signature = _b64url_decode(signature_b64)
    except ValueError as exc:
        raise InvalidTokenError(f"malformed signature: {exc}") from exc
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise InvalidTokenError("signature verification failed")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidTokenError(f"malformed payload: {exc}") from exc

    exp = payload.get("exp")
    if exp is not None and time.time() >= exp:
        raise ExpiredTokenError("token has expired")

    return payload
