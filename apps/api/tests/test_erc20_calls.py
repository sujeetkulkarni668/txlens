"""Unit tests for ERC-20 view-call return decoding."""
import unittest

from app.blockchain.erc20_calls import decode_string_return, decode_uint_return


def encode_dynamic_string(value: str) -> str:
    data_hex = value.encode().hex()
    padded = data_hex.ljust((len(data_hex) + 63) // 64 * 64, "0") if data_hex else ""
    return "0x" + format(32, "064x") + format(len(value), "064x") + padded


def encode_legacy_bytes32(value: str) -> str:
    return "0x" + value.encode().hex().ljust(64, "0")


class TestDecodeStringReturn(unittest.TestCase):
    def test_decodes_dynamic_string(self):
        self.assertEqual(decode_string_return(encode_dynamic_string("USDC")), "USDC")

    def test_decodes_longer_dynamic_string_spanning_multiple_words(self):
        self.assertEqual(decode_string_return(encode_dynamic_string("USD Coin Wrapped Token")), "USD Coin Wrapped Token")

    def test_decodes_legacy_bytes32_fallback(self):
        self.assertEqual(decode_string_return(encode_legacy_bytes32("MKR")), "MKR")

    def test_empty_calldata_returns_none(self):
        self.assertIsNone(decode_string_return("0x"))
        self.assertIsNone(decode_string_return(""))

    def test_garbage_returns_none_not_crash(self):
        self.assertIsNone(decode_string_return("0xzz"))


class TestDecodeUintReturn(unittest.TestCase):
    def test_decodes_decimals(self):
        self.assertEqual(decode_uint_return("0x" + format(6, "064x")), 6)

    def test_decodes_large_total_supply(self):
        supply = 1_000_000 * 10**18
        self.assertEqual(decode_uint_return("0x" + format(supply, "064x")), supply)

    def test_empty_returns_none(self):
        self.assertIsNone(decode_uint_return("0x"))


if __name__ == "__main__":
    unittest.main()
