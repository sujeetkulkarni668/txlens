"""Unit tests for SimulationService.

Uses a FakeBlockchainProvider (a plain implementation of the
BlockchainProvider ABC, no mocking framework needed) so these run fully
offline with only the stdlib.
"""
import unittest

from app.blockchain.exceptions import UnsupportedCapabilityError
from app.blockchain.provider import BlockchainProvider
from app.blockchain.schemas import CallResult, TraceCall, TraceCallResult
from app.simulation.service import SimulationService

CONTRACT = "0x4444444444444444444444444444444444444444"
FROM = "0x1111111111111111111111111111111111111111"
SPENDER = "0x2222222222222222222222222222222222222222"
RECIPIENT = "0x3333333333333333333333333333333333333333"

MAX_UINT256 = 2**256 - 1
TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL_TOPIC0 = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"


def word_address(addr: str) -> str:
    return addr[2:].lower().rjust(64, "0")


def word_uint(n: int) -> str:
    return format(n, "064x")


def approve_calldata(spender: str, amount: int) -> str:
    return "0x095ea7b3" + word_address(spender) + word_uint(amount)


class FakeProvider(BlockchainProvider):
    """Configurable stub — only the methods SimulationService actually
    calls are meaningfully implemented."""

    def __init__(self, *, call_result=None, call_exc=None, gas=21000, gas_exc=None, trace_result=None, trace_exc=None):
        self._call_result = call_result or CallResult(success=True, return_data="0x")
        self._call_exc = call_exc
        self._gas = gas
        self._gas_exc = gas_exc
        self._trace_result = trace_result
        self._trace_exc = trace_exc

    async def get_balance(self, address, block="latest"): raise NotImplementedError
    async def get_transaction(self, tx_hash): raise NotImplementedError
    async def get_transaction_receipt(self, tx_hash): raise NotImplementedError
    async def get_transaction_count(self, address, block="latest"): raise NotImplementedError
    async def get_code(self, address, block="latest"): raise NotImplementedError
    async def get_logs(self, **kwargs): raise NotImplementedError
    async def get_block(self, block="latest"): raise NotImplementedError

    async def call(self, *, to, data, block="latest"):
        if self._call_exc:
            raise self._call_exc
        return self._call_result

    async def estimate_gas(self, *, from_address, to, value, data):
        if self._gas_exc:
            raise self._gas_exc
        return self._gas

    async def trace_call(self, *, from_address, to, value, data):
        if self._trace_exc:
            raise self._trace_exc
        return self._trace_result


class TestSimulationServiceNoTrace(unittest.IsolatedAsyncioTestCase):
    """RPC endpoint without debug_traceCall — the common case for public
    endpoints like Base Sepolia's default RPC."""

    async def test_successful_approval_falls_back_to_calldata_decode(self):
        provider = FakeProvider(
            call_result=CallResult(success=True, return_data="0x"),
            gas=45000,
            trace_exc=UnsupportedCapabilityError("debug namespace disabled"),
        )
        service = SimulationService(provider)
        result = await service.simulate(
            chain="base-sepolia",
            from_address=FROM,
            to=CONTRACT,
            value="0",
            data=approve_calldata(SPENDER, 100),
        )
        self.assertTrue(result.success)
        self.assertEqual(result.gas_estimate, "45000")
        self.assertFalse(result.trace_supported)
        self.assertEqual(len(result.approvals), 1)
        self.assertEqual(result.approvals[0]["spender"], SPENDER.lower())
        self.assertEqual(result.approvals[0]["source"], "calldata_decode")
        self.assertTrue(any("tracing unsupported" in w for w in result.warnings))

    async def test_unlimited_approval_note_surfaces_in_decoded_actions(self):
        provider = FakeProvider(trace_exc=UnsupportedCapabilityError("no debug ns"))
        service = SimulationService(provider)
        result = await service.simulate(
            chain="base-sepolia",
            from_address=FROM,
            to=CONTRACT,
            value="0",
            data=approve_calldata(SPENDER, MAX_UINT256),
        )
        self.assertIn("unlimited approval amount (max uint256)", result.decoded_actions[0]["notes"])

    async def test_reverting_call_produces_no_fallback_effects(self):
        provider = FakeProvider(
            call_result=CallResult(success=False, return_data=None, error="insufficient balance"),
            trace_exc=UnsupportedCapabilityError("no debug ns"),
        )
        service = SimulationService(provider)
        result = await service.simulate(
            chain="base-sepolia", from_address=FROM, to=CONTRACT, value="0",
            data=approve_calldata(SPENDER, 1),
        )
        self.assertFalse(result.success)
        self.assertEqual(result.approvals, [])  # never claim an effect for a reverting call
        self.assertTrue(any("would revert" in w for w in result.warnings))

    async def test_contract_creation_not_simulated(self):
        provider = FakeProvider()
        service = SimulationService(provider)
        result = await service.simulate(
            chain="base-sepolia", from_address=FROM, to=None, value="0", data="0x600a"
        )
        self.assertIsNone(result.success)
        self.assertIsNone(result.trace_supported)
        self.assertTrue(any("contract-creation" in w for w in result.warnings))


class TestSimulationServiceWithTrace(unittest.IsolatedAsyncioTestCase):
    async def test_trace_supported_decodes_approval_event(self):
        log = {
            "address": CONTRACT,
            "topics": [APPROVAL_TOPIC0, "0x" + word_address(FROM), "0x" + word_address(SPENDER)],
            "data": "0x" + word_uint(250),
        }
        root = TraceCall(
            call_type="CALL", from_address=FROM, to_address=CONTRACT, value="0",
            input_data=approve_calldata(SPENDER, 250), logs=[log],
        )
        provider = FakeProvider(
            trace_result=TraceCallResult(success=True, root_call=root),
        )
        service = SimulationService(provider)
        result = await service.simulate(
            chain="base-sepolia", from_address=FROM, to=CONTRACT, value="0",
            data=approve_calldata(SPENDER, 250),
        )
        self.assertTrue(result.trace_supported)
        self.assertEqual(len(result.approvals), 1)
        self.assertEqual(result.approvals[0]["source"], "trace")
        self.assertEqual(result.approvals[0]["spender"], SPENDER.lower())
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0]["type"], "Approval")

    async def test_trace_captures_native_value_transfer(self):
        root = TraceCall(
            call_type="CALL", from_address=FROM, to_address=RECIPIENT,
            value=str(10**18), input_data="0x",
        )
        provider = FakeProvider(trace_result=TraceCallResult(success=True, root_call=root))
        service = SimulationService(provider)
        result = await service.simulate(
            chain="base-sepolia", from_address=FROM, to=RECIPIENT, value=str(10**18), data=None,
        )
        self.assertEqual(len(result.asset_changes), 1)
        self.assertEqual(result.asset_changes[0]["type"], "native")
        self.assertEqual(result.asset_changes[0]["amount"], str(10**18))

    async def test_unrecognized_log_reported_as_unknown_not_dropped(self):
        mystery_log = {"address": CONTRACT, "topics": ["0xdeadbeef" * 8], "data": "0x"}
        root = TraceCall(
            call_type="CALL", from_address=FROM, to_address=CONTRACT, value="0",
            input_data="0x12345678", logs=[mystery_log],
        )
        provider = FakeProvider(trace_result=TraceCallResult(success=True, root_call=root))
        service = SimulationService(provider)
        result = await service.simulate(
            chain="base-sepolia", from_address=FROM, to=CONTRACT, value="0", data="0x12345678",
        )
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0]["type"], "unknown")


if __name__ == "__main__":
    unittest.main()
