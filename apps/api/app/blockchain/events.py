"""Well-known ERC-20 event topic0 hashes and log-decoding helpers.

Same rationale as app/parser/selectors.py: these are the two events needed
for the simulation service to surface token movement/approvals from trace
logs. topic0 values are keccak256(event signature) — standard, publicly
documented constants (used by every block explorer/indexer), recorded here
as facts rather than computed, since this module has no crypto dependency.
Cross-check against a reference (e.g. an explorer's event page) before
relying on them in production; they have not been verified against a live
node in this environment (no network access here).
"""
from __future__ import annotations

from app.parser.selectors import CalldataDecodeError, decode_address, decode_uint256

TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL_TOPIC0 = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"


def decode_transfer_event(log: dict) -> dict | None:
    """Decode a standard ERC-20 Transfer(address indexed from, address
    indexed to, uint256 value) log. Returns None (never a guess) if the log
    doesn't match the expected shape."""
    topics = log.get("topics") or []
    if len(topics) < 3 or topics[0].lower() != TRANSFER_TOPIC0:
        return None
    try:
        from_addr = decode_address(topics[1][2:].rjust(64, "0"))
        to_addr = decode_address(topics[2][2:].rjust(64, "0"))
        data = (log.get("data") or "0x")[2:]
        amount = decode_uint256(data.rjust(64, "0")[:64])
    except CalldataDecodeError:
        return None
    return {
        "contract": log.get("address"),
        "from": from_addr,
        "to": to_addr,
        "amount": str(amount),
    }


def decode_approval_event(log: dict) -> dict | None:
    """Decode a standard ERC-20 Approval(address indexed owner, address
    indexed spender, uint256 value) log."""
    topics = log.get("topics") or []
    if len(topics) < 3 or topics[0].lower() != APPROVAL_TOPIC0:
        return None
    try:
        owner = decode_address(topics[1][2:].rjust(64, "0"))
        spender = decode_address(topics[2][2:].rjust(64, "0"))
        data = (log.get("data") or "0x")[2:]
        amount = decode_uint256(data.rjust(64, "0")[:64])
    except CalldataDecodeError:
        return None
    return {
        "contract": log.get("address"),
        "owner": owner,
        "spender": spender,
        "amount": str(amount),
    }
