"""Parser output types.

Deliberately implemented as stdlib dataclasses/enums rather than Pydantic
models: the parser has zero external dependencies, which keeps it usable
(and unit-testable) from any context, including the MCP server and ML
feature extraction, without pulling in the web framework stack. The API
layer (app/schemas/transaction.py) wraps this in a Pydantic response model
at the HTTP boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TransactionType(str, Enum):
    NATIVE_TRANSFER = "native_transfer"
    ERC20_TRANSFER = "erc20_transfer"
    ERC20_APPROVAL = "erc20_approval"
    CONTRACT_INTERACTION = "contract_interaction"
    UNKNOWN = "unknown"


class DecodeStatus(str, Enum):
    """Honesty signal for callers (product spec section 34: never pretend an
    unknown transaction was successfully decoded)."""

    DECODED = "decoded"
    PARTIALLY_DECODED = "partially_decoded"
    UNDECODED = "undecoded"


@dataclass
class ParsedTransaction:
    tx_type: TransactionType
    decode_status: DecodeStatus

    decoded_function: str | None = None
    contract_address: str | None = None
    parameters: dict[str, str] | None = None

    # Present only for erc20_transfer / erc20_approval / transferFrom-shaped
    # calldata. token_amount is the raw uint256 as a decimal string (never a
    # float — precision must not be lost).
    token_amount: str | None = None
    spender: str | None = None
    recipient: str | None = None
    sender: str | None = None
    is_unlimited_approval: bool = False

    notes: list[str] = field(default_factory=list)
