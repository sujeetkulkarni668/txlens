"""EVM input validation helpers (product spec section 26 — input
validation). Pure functions, no framework dependency, so they're testable
standalone and reusable from Pydantic validators, the MCP server, or
anywhere else that accepts an address/hex string from a caller.
"""
from __future__ import annotations

import re

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HEX_DATA_RE = re.compile(r"^0x([0-9a-fA-F]{2})*$")  # '0x' + whole bytes only
_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")

# Raw pattern strings (not the compiled objects above) for reuse in
# FastAPI `Path(pattern=...)` constraints on path parameters, so a
# malformed address/hash in the URL itself gets rejected with a 422
# before the handler ever runs, not several layers deeper.
ADDRESS_PATH_PATTERN = r"^0x[0-9a-fA-F]{40}$"
TX_HASH_PATH_PATTERN = r"^0x[0-9a-fA-F]{64}$"


def is_valid_tx_hash(value: str) -> bool:
    return isinstance(value, str) and bool(_TX_HASH_RE.match(value))


def is_valid_evm_address(value: str) -> bool:
    """Strict: exactly '0x' + 40 hex chars. Does not check EIP-55
    checksum casing — a lowercase or all-uppercase address is still
    valid, since plenty of legitimate tooling normalizes case."""
    return isinstance(value, str) and bool(_ADDRESS_RE.match(value))


def is_valid_hex_data(value: str) -> bool:
    """Calldata must be '0x' followed by a whole number of bytes (even
    number of hex digits) — an odd-length hex string is malformed input,
    not a transaction with 0.5 trailing bytes."""
    return isinstance(value, str) and bool(_HEX_DATA_RE.match(value))


def is_valid_decimal_string(value: str) -> bool:
    """For value/amount fields that must be a non-negative base-10
    integer string (wei amounts) — rejects '0x..', floats, negatives,
    and empty strings, all of which would otherwise silently coerce to 0
    or raise deep inside the pipeline instead of at the API boundary."""
    return isinstance(value, str) and value.isdigit()
