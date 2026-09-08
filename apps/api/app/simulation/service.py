"""Transaction simulation service (product spec section 10).

Distinct from actual blockchain execution — this never submits anything.
It combines three RPC capabilities:

  1. eth_call            — does the transaction succeed or revert?
  2. eth_estimateGas      — approximate gas cost
  3. debug_traceCall      — internal calls + logs, IF the RPC endpoint
                             supports it (product spec section 17); when it
                             doesn't, we fall back to the top-level calldata
                             decode from Phase 2's TransactionParser and
                             label every derived field with its source so a
                             caller can tell "confirmed by trace" apart from
                             "inferred from calldata, not yet executed".

Nothing here claims to guarantee the transaction's actual on-chain outcome
— gas prices, mempool state, and other transactions can all change the
result between simulation and submission.
"""
from __future__ import annotations

from collections.abc import Iterator

from app.blockchain.events import decode_approval_event, decode_transfer_event
from app.blockchain.exceptions import BlockchainProviderError, UnsupportedCapabilityError
from app.blockchain.provider import BlockchainProvider
from app.blockchain.schemas import TraceCall, TraceCallResult
from app.parser.parser import TransactionParser
from app.parser.schemas import DecodeStatus, ParsedTransaction, TransactionType
from app.simulation.schemas import SimulationResult


def _walk_frames(frame: TraceCall) -> Iterator[TraceCall]:
    yield frame
    for child in frame.calls:
        yield from _walk_frames(child)


def _decoded_action(parsed: ParsedTransaction) -> dict:
    return {
        "type": parsed.tx_type.value,
        "function": parsed.decoded_function,
        "decode_status": parsed.decode_status.value,
        "parameters": parsed.parameters,
        "notes": parsed.notes,
    }


class SimulationService:
    def __init__(self, provider: BlockchainProvider, parser: TransactionParser | None = None):
        self._provider = provider
        self._parser = parser or TransactionParser()

    async def simulate(
        self, *, chain: str, from_address: str, to: str | None, value: str, data: str | None
    ) -> SimulationResult:
        warnings: list[str] = []
        call_data = data or "0x"
        parsed = self._parser.parse(to=to, value=value, data=data)

        if to is None:
            warnings.append(
                "contract-creation transactions (no 'to' address) are not simulated in "
                "this phase"
            )
            return SimulationResult(
                success=None,
                gas_estimate=None,
                decoded_actions=[_decoded_action(parsed)],
                warnings=warnings,
                trace_supported=None,
            )

        success, call_warnings = await self._determine_success(
            from_address=from_address, to=to, data=call_data
        )
        warnings.extend(call_warnings)

        gas_estimate, gas_warnings = await self._estimate_gas(
            from_address=from_address, to=to, value=value, data=call_data
        )
        warnings.extend(gas_warnings)

        events: list[dict] = []
        asset_changes: list[dict] = []
        approvals: list[dict] = []
        trace_supported: bool | None

        try:
            trace_result = await self._provider.trace_call(
                from_address=from_address, to=to, value=value, data=call_data
            )
            trace_supported = True
            events, asset_changes, approvals = self._extract_from_trace(trace_result)
        except UnsupportedCapabilityError as exc:
            trace_supported = False
            warnings.append(
                f"internal-call tracing unsupported by this RPC endpoint ({exc}); "
                "asset changes and approvals below (if any) are inferred from the "
                "top-level calldata, not confirmed by execution"
            )
            fallback_asset_change, fallback_approval = self._fallback_from_calldata(
                parsed, to=to, success=success
            )
            if fallback_asset_change is not None:
                asset_changes.append(fallback_asset_change)
            if fallback_approval is not None:
                approvals.append(fallback_approval)
        except BlockchainProviderError as exc:
            trace_supported = None
            warnings.append(f"trace attempt failed: {exc}")

        return SimulationResult(
            success=success,
            gas_estimate=gas_estimate,
            decoded_actions=[_decoded_action(parsed)],
            asset_changes=asset_changes,
            approvals=approvals,
            events=events,
            warnings=warnings,
            trace_supported=trace_supported,
        )

    async def _determine_success(
        self, *, from_address: str, to: str, data: str
    ) -> tuple[bool | None, list[str]]:
        try:
            call_result = await self._provider.call(to=to, data=data)
        except BlockchainProviderError as exc:
            return None, [f"could not determine call outcome: {exc}"]
        if not call_result.success:
            return False, [f"call would revert: {call_result.error or 'unknown reason'}"]
        return True, []

    async def _estimate_gas(
        self, *, from_address: str, to: str, value: str, data: str
    ) -> tuple[str | None, list[str]]:
        try:
            gas = await self._provider.estimate_gas(
                from_address=from_address, to=to, value=value, data=data
            )
            return str(gas), []
        except BlockchainProviderError as exc:
            return None, [f"gas estimation failed: {exc}"]

    @staticmethod
    def _extract_from_trace(trace_result: TraceCallResult) -> tuple[list, list, list]:
        events: list[dict] = []
        asset_changes: list[dict] = []
        approvals: list[dict] = []

        for frame in _walk_frames(trace_result.root_call):
            if frame.value and int(frame.value) > 0 and frame.to_address:
                asset_changes.append(
                    {
                        "type": "native",
                        "from": frame.from_address,
                        "to": frame.to_address,
                        "amount": frame.value,
                        "source": "trace",
                    }
                )
            for log in frame.logs:
                transfer = decode_transfer_event(log)
                if transfer is not None:
                    events.append({"type": "Transfer", "source": "trace", **transfer})
                    asset_changes.append({"type": "erc20", "source": "trace", **transfer})
                    continue
                approval = decode_approval_event(log)
                if approval is not None:
                    events.append({"type": "Approval", "source": "trace", **approval})
                    approvals.append({"source": "trace", **approval})
                    continue
                events.append({"type": "unknown", "source": "trace", "raw": log})

        return events, asset_changes, approvals

    @staticmethod
    def _fallback_from_calldata(
        parsed: ParsedTransaction, *, to: str, success: bool | None
    ) -> tuple[dict | None, dict | None]:
        """Best-effort asset_change/approval derived purely from the
        decoded calldata when no trace is available. Only used for cleanly
        DECODED calls, and only when the call didn't already appear to
        revert — never presented as a confirmed on-chain effect (callers
        see `source: "calldata_decode"`, not `"trace"`)."""
        if parsed.decode_status != DecodeStatus.DECODED or success is False:
            return None, None

        if parsed.tx_type == TransactionType.ERC20_APPROVAL:
            approval = {
                "contract": to,
                "spender": parsed.spender,
                "amount": parsed.token_amount,
                "source": "calldata_decode",
                "note": "derived from calldata; not confirmed by trace",
            }
            return None, approval

        if parsed.tx_type == TransactionType.ERC20_TRANSFER:
            asset_change = {
                "type": "erc20",
                "contract": to,
                "from": parsed.sender,
                "to": parsed.recipient,
                "amount": parsed.token_amount,
                "source": "calldata_decode",
                "note": "derived from calldata; not confirmed by trace",
            }
            return asset_change, None

        return None, None
