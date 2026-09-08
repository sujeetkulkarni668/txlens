"""Structured return types for BlockchainProvider methods.

Stdlib dataclasses (not Pydantic) so this module — like the parser — has no
external dependencies and can be unit-tested without installing anything.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TransactionData:
    hash: str
    from_address: str
    to_address: str | None
    value: str  # wei, decimal string
    data: str
    block_number: int | None
    nonce: int
    gas: int
    gas_price: str | None


@dataclass
class TransactionReceipt:
    transaction_hash: str
    status: bool | None  # None if the receipt doesn't report status (rare, pre-Byzantium)
    block_number: int
    gas_used: int
    logs: list[dict] = field(default_factory=list)
    contract_address: str | None = None


@dataclass
class Block:
    number: int
    hash: str
    timestamp: int
    transactions: list[str] = field(default_factory=list)  # tx hashes


@dataclass
class CallResult:
    success: bool
    return_data: str | None  # hex-encoded return value, if success
    error: str | None = None  # revert reason / error message, if not success


@dataclass
class TraceCall:
    """A single call frame from a call-tracer style trace."""

    call_type: str  # CALL, DELEGATECALL, STATICCALL, CREATE, ...
    from_address: str
    to_address: str | None
    value: str  # wei, decimal string
    input_data: str
    output_data: str | None = None
    error: str | None = None
    calls: list["TraceCall"] = field(default_factory=list)
    logs: list[dict] = field(default_factory=list)


@dataclass
class TraceCallResult:
    success: bool
    root_call: TraceCall
    error: str | None = None
