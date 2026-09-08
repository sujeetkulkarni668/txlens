"""Unit tests for TokenIntelligenceService / ContractIntelligenceService,
using a hand-written FakeProvider (no mocking framework needed)."""
import unittest

from app.blockchain.erc20_calls import DECIMALS_SELECTOR, NAME_SELECTOR, SYMBOL_SELECTOR, TOTAL_SUPPLY_SELECTOR
from app.blockchain.provider import BlockchainProvider
from app.blockchain.schemas import CallResult
from app.intelligence.contract_service import ContractIntelligenceService
from app.intelligence.token_service import TokenIntelligenceService

CONTRACT = "0x4444444444444444444444444444444444444444"
EOA = "0x1111111111111111111111111111111111111111"


def encode_dynamic_string(value: str) -> str:
    data_hex = value.encode().hex()
    padded = data_hex.ljust((len(data_hex) + 63) // 64 * 64, "0") if data_hex else ""
    return "0x" + format(32, "064x") + format(len(value), "064x") + padded


class FakeProvider(BlockchainProvider):
    def __init__(self, *, code="0x", call_responses=None):
        self._code = code
        self._call_responses = call_responses or {}

    async def get_balance(self, address, block="latest"): raise NotImplementedError
    async def get_transaction(self, tx_hash): raise NotImplementedError
    async def get_transaction_receipt(self, tx_hash): raise NotImplementedError
    async def get_transaction_count(self, address, block="latest"): raise NotImplementedError
    async def get_logs(self, **kwargs): raise NotImplementedError
    async def get_block(self, block="latest"): raise NotImplementedError
    async def estimate_gas(self, **kwargs): raise NotImplementedError
    async def trace_call(self, **kwargs): raise NotImplementedError

    async def get_code(self, address, block="latest"):
        return self._code

    async def call(self, *, to, data, block="latest"):
        if data in self._call_responses:
            return self._call_responses[data]
        return CallResult(success=False, return_data=None, error="unrecognized selector")


class TestTokenIntelligenceService(unittest.IsolatedAsyncioTestCase):
    async def test_eoa_short_circuits_with_no_calls(self):
        provider = FakeProvider(code="0x")
        result = await TokenIntelligenceService(provider).inspect(EOA)
        self.assertFalse(result["is_contract"])
        self.assertIsNone(result["symbol"])

    async def test_full_token_read(self):
        provider = FakeProvider(
            code="0x6001",
            call_responses={
                SYMBOL_SELECTOR: CallResult(success=True, return_data=encode_dynamic_string("USDC")),
                NAME_SELECTOR: CallResult(success=True, return_data=encode_dynamic_string("USD Coin")),
                DECIMALS_SELECTOR: CallResult(success=True, return_data="0x" + format(6, "064x")),
                TOTAL_SUPPLY_SELECTOR: CallResult(success=True, return_data="0x" + format(10**18, "064x")),
            },
        )
        result = await TokenIntelligenceService(provider).inspect(CONTRACT)
        self.assertTrue(result["is_contract"])
        self.assertEqual(result["symbol"], "USDC")
        self.assertEqual(result["name"], "USD Coin")
        self.assertEqual(result["decimals"], 6)
        self.assertEqual(result["total_supply"], str(10**18))

    async def test_reverting_call_yields_none_not_crash(self):
        provider = FakeProvider(
            code="0x6001",
            call_responses={
                SYMBOL_SELECTOR: CallResult(success=False, return_data=None, error="revert"),
            },
        )
        result = await TokenIntelligenceService(provider).inspect(CONTRACT)
        self.assertIsNone(result["symbol"])
        self.assertTrue(result["is_contract"])

    async def test_notes_flag_missing_verification_capability(self):
        provider = FakeProvider(code="0x6001")
        result = await TokenIntelligenceService(provider).inspect(CONTRACT)
        self.assertTrue(any("indexer" in n for n in result["notes"]))


class TestContractIntelligenceService(unittest.IsolatedAsyncioTestCase):
    async def test_eoa_reports_no_code(self):
        provider = FakeProvider(code="0x")
        result = await ContractIntelligenceService(provider).inspect(EOA)
        self.assertFalse(result["is_contract"])
        self.assertEqual(result["bytecode_size_bytes"], 0)

    async def test_contract_reports_bytecode_size_and_unknown_verification(self):
        provider = FakeProvider(code="0x" + "60" * 100)
        result = await ContractIntelligenceService(provider).inspect(CONTRACT)
        self.assertTrue(result["is_contract"])
        self.assertEqual(result["bytecode_size_bytes"], 100)
        self.assertIsNone(result["source_verified"])  # unknown, never guessed


if __name__ == "__main__":
    unittest.main()
