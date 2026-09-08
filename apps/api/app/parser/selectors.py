"""Known ERC-20 function selectors and raw ABI-word decoding helpers.

Hand-rolled rather than pulling in eth-abi/web3 for ABI decoding: the set of
functions TxLens needs to recognize at this phase (plain ERC-20
transfer/approve/transferFrom) is small and fixed, so a general-purpose ABI
decoder would be an unnecessary dependency (see product spec section 33 —
avoid unnecessary abstractions). Arbitrary-contract decoding using a
verified ABI is added alongside contract intelligence in a later phase and
will use a real ABI decoder at that point, since selector-only knowledge
stops being enough once the shape of the ABI isn't already known.

Selectors below are keccak256(signature)[:4], recorded as boolean facts,
not computed here.
"""
from __future__ import annotations

# selector (0x + 8 hex chars) -> (human-readable signature, param types)
KNOWN_SELECTORS: dict[str, tuple[str, list[str]]] = {
    "0xa9059cbb": ("transfer(address,uint256)", ["address", "uint256"]),
    "0x095ea7b3": ("approve(address,uint256)", ["address", "uint256"]),
    "0x23b872dd": (
        "transferFrom(address,address,uint256)",
        ["address", "address", "uint256"],
    ),
}

WORD_HEX_LEN = 64  # 32 bytes, ABI-encoded word width


class CalldataDecodeError(ValueError):
    """Raised when calldata cannot be split into well-formed 32-byte words."""


def split_words(calldata_hex_no_prefix: str) -> list[str]:
    """Split ABI-encoded parameter data (after the 4-byte selector, no
    leading '0x') into 32-byte (64 hex char) words.

    Raises CalldataDecodeError if the data isn't a clean multiple of 32
    bytes or contains non-hex characters — callers must treat that as
    "undecoded", never guess at the missing bytes.
    """
    if len(calldata_hex_no_prefix) % WORD_HEX_LEN != 0:
        raise CalldataDecodeError(
            f"calldata length {len(calldata_hex_no_prefix)} is not a multiple of "
            f"{WORD_HEX_LEN} hex chars (32 bytes) — likely truncated or malformed"
        )
    try:
        int(calldata_hex_no_prefix or "0", 16)
    except ValueError as exc:
        raise CalldataDecodeError("calldata contains non-hexadecimal characters") from exc

    return [
        calldata_hex_no_prefix[i : i + WORD_HEX_LEN]
        for i in range(0, len(calldata_hex_no_prefix), WORD_HEX_LEN)
    ]


def decode_address(word_hex: str) -> str:
    """Decode a 32-byte ABI word as a left-padded 20-byte address."""
    if len(word_hex) != WORD_HEX_LEN:
        raise CalldataDecodeError(f"expected a {WORD_HEX_LEN}-char word, got {len(word_hex)}")
    return "0x" + word_hex[-40:]


def decode_uint256(word_hex: str) -> int:
    """Decode a 32-byte ABI word as an unsigned integer."""
    if len(word_hex) != WORD_HEX_LEN:
        raise CalldataDecodeError(f"expected a {WORD_HEX_LEN}-char word, got {len(word_hex)}")
    return int(word_hex, 16)
