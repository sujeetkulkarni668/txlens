"""Standard ERC-20 view-function selectors and ABI return decoding.

Same rationale as parser/selectors.py: these four selectors are fixed,
well-known constants, so hand-decoding avoids pulling in a full ABI
library for a handful of read calls.
"""
from __future__ import annotations

from app.parser.selectors import CalldataDecodeError, decode_uint256

SYMBOL_SELECTOR = "0x95d89b41"
NAME_SELECTOR = "0x06fdde03"
DECIMALS_SELECTOR = "0x313ce567"
TOTAL_SUPPLY_SELECTOR = "0x18160ddd"

WORD_HEX_LEN = 64


def decode_string_return(return_data: str) -> str | None:
    """Decode an eth_call return value as an ABI dynamic `string`, with a
    fallback to the legacy fixed `bytes32` encoding some older tokens
    (e.g. MKR) use for symbol()/name(). Returns None (never a guess) if
    neither decode succeeds."""
    if not return_data or return_data == "0x":
        return None
    body = return_data[2:]

    # Dynamic string: word[0] = offset (bytes), word[at offset] = length,
    # followed by the UTF-8 bytes, right-padded to a 32-byte boundary.
    if len(body) >= WORD_HEX_LEN:
        try:
            offset_bytes = decode_uint256(body[:WORD_HEX_LEN])
            offset_hex = offset_bytes * 2
            length_word = body[offset_hex : offset_hex + WORD_HEX_LEN]
            if len(length_word) == WORD_HEX_LEN:
                length_bytes = decode_uint256(length_word)
                data_start = offset_hex + WORD_HEX_LEN
                data_hex = body[data_start : data_start + length_bytes * 2]
                if len(data_hex) == length_bytes * 2:
                    return bytes.fromhex(data_hex).decode("utf-8", errors="replace")
        except (CalldataDecodeError, ValueError):
            pass

    # Legacy bytes32 fallback: raw ASCII, null-padded.
    try:
        raw = bytes.fromhex(body[:WORD_HEX_LEN])
        decoded = raw.decode("utf-8", errors="ignore").rstrip("\x00").strip()
        return decoded or None
    except ValueError:
        return None


def decode_uint_return(return_data: str) -> int | None:
    if not return_data or return_data == "0x":
        return None
    body = return_data[2:].rjust(WORD_HEX_LEN, "0")[:WORD_HEX_LEN]
    try:
        return decode_uint256(body)
    except CalldataDecodeError:
        return None
