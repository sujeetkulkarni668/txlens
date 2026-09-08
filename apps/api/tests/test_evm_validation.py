"""Unit tests for EVM input validation helpers."""
import unittest

from app.validation.evm import is_valid_decimal_string, is_valid_evm_address, is_valid_hex_data

VALID_ADDRESS = "0x1111111111111111111111111111111111111111"


class TestIsValidEvmAddress(unittest.TestCase):
    def test_valid_lowercase_address(self):
        self.assertTrue(is_valid_evm_address(VALID_ADDRESS))

    def test_valid_uppercase_address(self):
        # The '0x' prefix is conventionally lowercase even when the hex
        # body is all-uppercase — this is a realistic uppercase address,
        # not `VALID_ADDRESS.upper()` (which would incorrectly uppercase
        # the prefix to '0X', something no real tooling actually emits).
        self.assertTrue(is_valid_evm_address("0x" + VALID_ADDRESS[2:].upper()))

    def test_valid_mixed_case_checksum_style_address(self):
        self.assertTrue(is_valid_evm_address("0xAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAaAa"))

    def test_missing_0x_prefix_rejected(self):
        self.assertFalse(is_valid_evm_address(VALID_ADDRESS[2:]))

    def test_too_short_rejected(self):
        self.assertFalse(is_valid_evm_address("0x1111"))

    def test_too_long_rejected(self):
        self.assertFalse(is_valid_evm_address(VALID_ADDRESS + "11"))

    def test_non_hex_characters_rejected(self):
        self.assertFalse(is_valid_evm_address("0x11111111111111111111111111111111111zzz"))

    def test_non_string_input_rejected_not_crashed(self):
        self.assertFalse(is_valid_evm_address(None))
        self.assertFalse(is_valid_evm_address(12345))


class TestIsValidHexData(unittest.TestCase):
    def test_empty_calldata_is_valid(self):
        self.assertTrue(is_valid_hex_data("0x"))

    def test_whole_bytes_valid(self):
        self.assertTrue(is_valid_hex_data("0xa9059cbb"))

    def test_odd_length_hex_rejected(self):
        self.assertFalse(is_valid_hex_data("0xabc"))

    def test_missing_prefix_rejected(self):
        self.assertFalse(is_valid_hex_data("a9059cbb"))

    def test_non_hex_rejected(self):
        self.assertFalse(is_valid_hex_data("0xzzzz"))


class TestIsValidDecimalString(unittest.TestCase):
    def test_zero_is_valid(self):
        self.assertTrue(is_valid_decimal_string("0"))

    def test_large_wei_value_is_valid(self):
        self.assertTrue(is_valid_decimal_string(str(10**30)))

    def test_hex_string_rejected(self):
        self.assertFalse(is_valid_decimal_string("0x10"))

    def test_negative_rejected(self):
        self.assertFalse(is_valid_decimal_string("-5"))

    def test_float_rejected(self):
        self.assertFalse(is_valid_decimal_string("1.5"))

    def test_empty_string_rejected(self):
        self.assertFalse(is_valid_decimal_string(""))


if __name__ == "__main__":
    unittest.main()
