"""BlockchainProvider abstraction (product spec section 9).

All blockchain reads in TxLens go through this interface so RPC providers
(and eventually non-EVM chains) can be swapped without touching callers.
Nothing in TxLens should import a specific RPC vendor SDK directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.blockchain.schemas import (
    Block,
    CallResult,
    TransactionData,
    TransactionReceipt,
    TraceCallResult,
)


class BlockchainProvider(ABC):
    """Read-only EVM chain access. No method on this interface ever signs
    or submits a transaction — TxLens never holds private keys."""

    @abstractmethod
    async def get_balance(self, address: str, block: str = "latest") -> int:
        """Native token balance in wei."""

    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> TransactionData | None:
        """Returns None if the transaction is not found (e.g. not yet mined,
        or wrong hash) — never fabricate a transaction."""

    @abstractmethod
    async def get_transaction_receipt(self, tx_hash: str) -> TransactionReceipt | None:
        """Returns None if no receipt exists yet."""

    @abstractmethod
    async def get_transaction_count(self, address: str, block: str = "latest") -> int:
        """Nonce / transaction count for an address."""

    @abstractmethod
    async def get_code(self, address: str, block: str = "latest") -> str:
        """Returns '0x' for an EOA (no code), or the contract bytecode."""

    @abstractmethod
    async def get_logs(
        self,
        *,
        address: str | None = None,
        from_block: str = "latest",
        to_block: str = "latest",
        topics: list[str] | None = None,
    ) -> list[dict]:
        """Raw event logs matching the given filter."""

    @abstractmethod
    async def get_block(self, block: str = "latest") -> Block:
        ...

    @abstractmethod
    async def call(self, *, to: str, data: str, block: str = "latest") -> CallResult:
        """Read-only contract call (eth_call). Never mutates chain state."""

    @abstractmethod
    async def estimate_gas(self, *, from_address: str, to: str | None, value: str, data: str) -> int:
        ...

    @abstractmethod
    async def trace_call(
        self, *, from_address: str, to: str | None, value: str, data: str
    ) -> TraceCallResult:
        """Simulate a call and return its internal call tree + logs
        (product spec section 17).

        Must raise UnsupportedCapabilityError — never fabricate a trace —
        if the underlying node doesn't expose a tracing method. Callers
        (the simulation service) are required to handle that explicitly
        and report `trace_supported: false` rather than treat the absence
        of an exception as "no internal calls occurred".
        """
