"""Unit tests for TransactionParser (product spec section 8).

Pure stdlib unittest — no external dependencies required to run these.
"""
import unittest

from app.parser.parser import TransactionParser
from app.parser.schemas import DecodeStatus, TransactionType

RECIPIENT = "0x1111111111111111111111111111111111111111"
SPENDER = "0x2222222222222222222222222222222222222222"
FROM_ADDR = "0x3333333333333333333333333333333333333333"
CONTRACT = "0x4444444444444444444444444444444444444444"

MAX_UINT256 = 2**256 - 1


def word_address(addr: str) -> str:
    return addr[2:].lower().rjust(64, "0")


def word_uint(n: int) -> str:
    return format(n, "064x")


class TestNativeTransfer(unittest.TestCase):
    def setUp(self):
        self.parser = TransactionParser()

    def test_empty_data_is_native_transfer(self):
        result = self.parser.parse(to=RECIPIENT, value="1000000000000000000", data=None)
        self.assertEqual(result.tx_type, TransactionType.NATIVE_TRANSFER)
        self.assertEqual(result.decode_status, DecodeStatus.DECODED)
        self.assertEqual(result.recipient, RECIPIENT)
        self.assertEqual(result.token_amount, "1000000000000000000")

    def test_literal_0x_data_is_native_transfer(self):
        result = self.parser.parse(to=RECIPIENT, value="0", data="0x")
        self.assertEqual(result.tx_type, TransactionType.NATIVE_TRANSFER)

    def test_zero_value_native_transfer_still_classified(self):
        result = self.parser.parse(to=RECIPIENT, value="0", data="")
        self.assertEqual(result.tx_type, TransactionType.NATIVE_TRANSFER)
        self.assertEqual(result.decode_status, DecodeStatus.DECODED)


class TestErc20Transfer(unittest.TestCase):
    def setUp(self):
        self.parser = TransactionParser()

    def build_transfer_calldata(self, recipient: str, amount: int) -> str:
        return "0xa9059cbb" + word_address(recipient) + word_uint(amount)

    def test_decodes_transfer(self):
        calldata = self.build_transfer_calldata(RECIPIENT, 5_000_000)
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.tx_type, TransactionType.ERC20_TRANSFER)
        self.assertEqual(result.decode_status, DecodeStatus.DECODED)
        self.assertEqual(result.decoded_function, "transfer(address,uint256)")
        self.assertEqual(result.recipient, RECIPIENT.lower())
        self.assertEqual(result.token_amount, "5000000")
        self.assertEqual(result.contract_address, CONTRACT)

    def test_case_insensitive_selector(self):
        calldata = self.build_transfer_calldata(RECIPIENT, 42).upper().replace("0X", "0x")
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.tx_type, TransactionType.ERC20_TRANSFER)

    def test_decodes_transfer_from(self):
        calldata = (
            "0x23b872dd" + word_address(FROM_ADDR) + word_address(RECIPIENT) + word_uint(7)
        )
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.tx_type, TransactionType.ERC20_TRANSFER)
        self.assertEqual(result.sender, FROM_ADDR.lower())
        self.assertEqual(result.recipient, RECIPIENT.lower())
        self.assertEqual(result.token_amount, "7")


class TestErc20Approval(unittest.TestCase):
    def setUp(self):
        self.parser = TransactionParser()

    def test_decodes_approval(self):
        calldata = "0x095ea7b3" + word_address(SPENDER) + word_uint(100)
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.tx_type, TransactionType.ERC20_APPROVAL)
        self.assertEqual(result.spender, SPENDER.lower())
        self.assertEqual(result.token_amount, "100")
        self.assertNotIn("unlimited approval amount (max uint256)", result.notes)

    def test_flags_unlimited_approval(self):
        calldata = "0x095ea7b3" + word_address(SPENDER) + word_uint(MAX_UINT256)
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.tx_type, TransactionType.ERC20_APPROVAL)
        self.assertIn("unlimited approval amount (max uint256)", result.notes)


class TestUnknownAndMalformed(unittest.TestCase):
    def setUp(self):
        self.parser = TransactionParser()

    def test_unknown_selector_is_contract_interaction_undecoded(self):
        calldata = "0xdeadbeef" + word_uint(1)
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.tx_type, TransactionType.CONTRACT_INTERACTION)
        self.assertEqual(result.decode_status, DecodeStatus.UNDECODED)
        self.assertIsNone(result.decoded_function)
        self.assertTrue(any("unrecognized function selector" in n for n in result.notes))

    def test_truncated_selector_is_undecoded(self):
        result = self.parser.parse(to=CONTRACT, value="0", data="0xa905")
        self.assertEqual(result.tx_type, TransactionType.UNKNOWN)
        self.assertEqual(result.decode_status, DecodeStatus.UNDECODED)

    def test_known_selector_but_truncated_params_is_partially_decoded(self):
        # transfer() selector present, but only 1 of 2 expected words follow.
        calldata = "0xa9059cbb" + word_address(RECIPIENT)
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.decode_status, DecodeStatus.PARTIALLY_DECODED)
        self.assertEqual(result.decoded_function, "transfer(address,uint256)")
        self.assertIsNone(result.token_amount)

    def test_malformed_hex_is_partially_decoded_not_crashed(self):
        calldata = "0xa9059cbb" + "zz" * 32 + word_uint(1)
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertEqual(result.decode_status, DecodeStatus.PARTIALLY_DECODED)
        self.assertTrue(any("malformed" in n for n in result.notes))

    def test_never_fabricates_success_for_unknown_function(self):
        calldata = "0x12345678" + word_uint(999)
        result = self.parser.parse(to=CONTRACT, value="0", data=calldata)
        self.assertNotEqual(result.decode_status, DecodeStatus.DECODED)

    def test_contract_creation_no_to_address(self):
        result = self.parser.parse(to=None, value="0", data="0x600a600c60003960")
        self.assertEqual(result.tx_type, TransactionType.UNKNOWN)
        self.assertEqual(result.decode_status, DecodeStatus.UNDECODED)
        self.assertTrue(any("contract creation" in n for n in result.notes))


if __name__ == "__main__":
    unittest.main()
