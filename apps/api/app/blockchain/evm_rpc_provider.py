"""JSON-RPC implementation of BlockchainProvider.

Uses stdlib `urllib` rather than `httpx`: this keeps the RPC transport
dependency-free and independently unit-testable (see
tests/test_evm_rpc_provider.py), and the request volume here doesn't need
connection pooling. Higher-throughput call sites (AI/MCP) still use httpx
per requirements.txt.

Never hard-codes a specific RPC vendor — the endpoint is fully
configuration-driven (product spec section 9).
"""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from itertools import count
from typing import Any

from app.blockchain.exceptions import RpcError, RpcTransportError, UnsupportedCapabilityError
from app.blockchain.provider import BlockchainProvider
from app.blockchain.schemas import (
    Block,
    CallResult,
    TraceCall,
    TraceCallResult,
    TransactionData,
    TransactionReceipt,
)

_DEFAULT_TIMEOUT_SECONDS = 10


class EVMRPCProvider(BlockchainProvider):
    def __init__(self, rpc_url: str, *, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS):
        if not rpc_url:
            raise ValueError("rpc_url must be set (see EVM_RPC_URL in .env)")
        self._rpc_url = rpc_url
        self._timeout_seconds = timeout_seconds
        self._id_counter = count(1)
        # Cached once known, so we don't re-probe a node that has already
        # told us debug_traceCall isn't available.
        self._trace_supported: bool | None = None

    # ── transport ──────────────────────────────────────────────────────

    def _sync_rpc_call(self, method: str, params: list[Any]) -> Any:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": next(self._id_counter), "method": method, "params": params}
        ).encode("utf-8")
        request = urllib.request.Request(
            self._rpc_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read()
        except urllib.error.URLError as exc:
            raise RpcTransportError(f"failed to reach RPC endpoint: {exc}") from exc

        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RpcTransportError(f"RPC endpoint returned non-JSON response: {exc}") from exc

        if "error" in decoded:
            err = decoded["error"]
            raise RpcError(code=err.get("code", -1), message=err.get("message", "unknown error"))

        return decoded.get("result")

    async def _rpc_call(self, method: str, params: list[Any] | None = None) -> Any:
        return await asyncio.to_thread(self._sync_rpc_call, method, params or [])

    # ── BlockchainProvider ────────────────────────────────────────────

    async def get_balance(self, address: str, block: str = "latest") -> int:
        result = await self._rpc_call("eth_getBalance", [address, block])
        return int(result, 16)

    async def get_transaction(self, tx_hash: str) -> TransactionData | None:
        result = await self._rpc_call("eth_getTransactionByHash", [tx_hash])
        if result is None:
            return None
        return TransactionData(
            hash=result["hash"],
            from_address=result["from"],
            to_address=result.get("to"),
            value=str(int(result.get("value", "0x0"), 16)),
            data=result.get("input", "0x"),
            block_number=(int(result["blockNumber"], 16) if result.get("blockNumber") else None),
            nonce=int(result.get("nonce", "0x0"), 16),
            gas=int(result.get("gas", "0x0"), 16),
            gas_price=(str(int(result["gasPrice"], 16)) if result.get("gasPrice") else None),
        )

    async def get_transaction_receipt(self, tx_hash: str) -> TransactionReceipt | None:
        result = await self._rpc_call("eth_getTransactionReceipt", [tx_hash])
        if result is None:
            return None
        status_raw = result.get("status")
        return TransactionReceipt(
            transaction_hash=result["transactionHash"],
            status=(bool(int(status_raw, 16)) if status_raw is not None else None),
            block_number=int(result["blockNumber"], 16),
            gas_used=int(result.get("gasUsed", "0x0"), 16),
            logs=result.get("logs", []),
            contract_address=result.get("contractAddress"),
        )

    async def get_transaction_count(self, address: str, block: str = "latest") -> int:
        result = await self._rpc_call("eth_getTransactionCount", [address, block])
        return int(result, 16)

    async def get_code(self, address: str, block: str = "latest") -> str:
        return await self._rpc_call("eth_getCode", [address, block])

    async def get_logs(
        self,
        *,
        address: str | None = None,
        from_block: str = "latest",
        to_block: str = "latest",
        topics: list[str] | None = None,
    ) -> list[dict]:
        filter_params: dict[str, Any] = {"fromBlock": from_block, "toBlock": to_block}
        if address is not None:
            filter_params["address"] = address
        if topics is not None:
            filter_params["topics"] = topics
        result = await self._rpc_call("eth_getLogs", [filter_params])
        return result or []

    async def get_block(self, block: str = "latest") -> Block:
        result = await self._rpc_call("eth_getBlockByNumber", [block, False])
        if result is None:
            raise RpcError(code=-32000, message=f"block '{block}' not found")
        return Block(
            number=int(result["number"], 16),
            hash=result["hash"],
            timestamp=int(result["timestamp"], 16),
            transactions=result.get("transactions", []),
        )

    async def call(self, *, to: str, data: str, block: str = "latest") -> CallResult:
        call_params = {"to": to, "data": data}
        try:
            result = await self._rpc_call("eth_call", [call_params, block])
            return CallResult(success=True, return_data=result)
        except RpcError as exc:
            # A revert surfaces as a JSON-RPC error — report it as a failed
            # call, not a transport failure.
            return CallResult(success=False, return_data=None, error=exc.message)

    async def estimate_gas(
        self, *, from_address: str, to: str | None, value: str, data: str
    ) -> int:
        params: dict[str, Any] = {"from": from_address, "value": hex(int(value)), "data": data}
        if to is not None:
            params["to"] = to
        result = await self._rpc_call("eth_estimateGas", [params])
        return int(result, 16)

    async def trace_call(
        self, *, from_address: str, to: str | None, value: str, data: str
    ) -> TraceCallResult:
        if self._trace_supported is False:
            raise UnsupportedCapabilityError(
                "debug_traceCall is not available on this RPC endpoint "
                f"({self._rpc_url}) — determined on a prior call"
            )

        call_object: dict[str, Any] = {"from": from_address, "value": hex(int(value)), "data": data}
        if to is not None:
            call_object["to"] = to
        tracer_config = {"tracer": "callTracer", "tracerConfig": {"withLog": True}}

        try:
            result = await self._rpc_call("debug_traceCall", [call_object, "latest", tracer_config])
        except RpcError as exc:
            # Nodes without the debug namespace enabled return a
            # method-not-found (or similarly shaped) RPC error here, not a
            # populated trace with an error field — this is a capability
            # gap, not a reverted call, so surface it as unsupported rather
            # than as a failed simulation.
            self._trace_supported = False
            raise UnsupportedCapabilityError(
                f"debug_traceCall unavailable or rejected by {self._rpc_url}: {exc.message}"
            ) from exc

        self._trace_supported = True
        root_call = self._parse_trace_frame(result)
        return TraceCallResult(success=(root_call.error is None), root_call=root_call)

    @staticmethod
    def _parse_trace_frame(frame: dict) -> TraceCall:
        return TraceCall(
            call_type=frame.get("type", "CALL"),
            from_address=frame.get("from", ""),
            to_address=frame.get("to"),
            value=str(int(frame.get("value", "0x0"), 16)) if frame.get("value") else "0",
            input_data=frame.get("input", "0x"),
            output_data=frame.get("output"),
            error=frame.get("error"),
            calls=[EVMRPCProvider._parse_trace_frame(c) for c in frame.get("calls", [])],
            logs=frame.get("logs", []),
        )
