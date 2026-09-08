"""EVM transaction parser (product spec section 8).

Identifies transaction type from raw fields (to, value, data) and decodes
known ERC-20 call shapes. Never fabricates a decode: unknown selectors and
malformed calldata are reported honestly via `DecodeStatus` and `notes`
rather than guessed at (product spec section 34).
"""
from __future__ import annotations

from app.parser.schemas import DecodeStatus, ParsedTransaction, TransactionType
from app.parser.selectors import (
    KNOWN_SELECTORS,
    CalldataDecodeError,
    decode_address,
    decode_uint256,
    split_words,
)

SELECTOR_HEX_LEN = 8  # 4 bytes


def _normalize_data(data: str | None) -> str:
    """Lowercase, strip an optional 0x prefix's presence-check, always
    return a value starting with '0x' (possibly just '0x' for empty
    calldata)."""
    if not data:
        return "0x"
    d = data.strip().lower()
    if not d.startswith("0x"):
        d = "0x" + d
    return d


class TransactionParser:
    """Stateless parser — safe to reuse across requests."""

    def parse(self, *, to: str | None, value: str, data: str | None) -> ParsedTransaction:
        """Parse a raw transaction into a typed, honestly-labeled result.

        Args:
            to: recipient/contract address, or None for a contract-creation
                transaction.
            value: native value in wei, as a decimal string.
            data: calldata, as a '0x'-prefixed hex string (or None/empty).
        """
        normalized = _normalize_data(data)

        if to is None:
            # Contract creation isn't one of the five classified types in
            # the product spec — report it honestly rather than forcing it
            # into a bucket that would misrepresent it.
            return ParsedTransaction(
                tx_type=TransactionType.UNKNOWN,
                decode_status=DecodeStatus.UNDECODED,
                notes=["transaction has no 'to' address (contract creation) — not classified"],
            )

        if normalized == "0x":
            return ParsedTransaction(
                tx_type=TransactionType.NATIVE_TRANSFER,
                decode_status=DecodeStatus.DECODED,
                recipient=to,
                token_amount=value,
                notes=["no calldata present"],
            )

        body = normalized[2:]  # strip '0x'
        if len(body) < SELECTOR_HEX_LEN:
            return ParsedTransaction(
                tx_type=TransactionType.UNKNOWN,
                decode_status=DecodeStatus.UNDECODED,
                contract_address=to,
                notes=[
                    f"calldata is only {len(body)} hex chars — too short to contain a "
                    "4-byte function selector"
                ],
            )

        selector = "0x" + body[:SELECTOR_HEX_LEN]
        params_hex = body[SELECTOR_HEX_LEN:]

        known = KNOWN_SELECTORS.get(selector)
        if known is None:
            return ParsedTransaction(
                tx_type=TransactionType.CONTRACT_INTERACTION,
                decode_status=DecodeStatus.UNDECODED,
                contract_address=to,
                decoded_function=None,
                notes=[f"unrecognized function selector {selector} — parameters not decoded"],
            )

        signature, param_types = known
        try:
            words = split_words(params_hex)
        except CalldataDecodeError as exc:
            return ParsedTransaction(
                tx_type=self._type_for_selector(selector),
                decode_status=DecodeStatus.PARTIALLY_DECODED,
                contract_address=to,
                decoded_function=signature,
                notes=[f"known function selector but calldata is malformed: {exc}"],
            )

        if len(words) < len(param_types):
            return ParsedTransaction(
                tx_type=self._type_for_selector(selector),
                decode_status=DecodeStatus.PARTIALLY_DECODED,
                contract_address=to,
                decoded_function=signature,
                notes=[
                    f"expected {len(param_types)} parameter word(s), found {len(words)} — "
                    "calldata may be truncated; parameters not decoded"
                ],
            )

        return self._decode_known(selector, signature, to, words)

    @staticmethod
    def _type_for_selector(selector: str) -> TransactionType:
        if selector == "0xa9059cbb":
            return TransactionType.ERC20_TRANSFER
        if selector == "0x095ea7b3":
            return TransactionType.ERC20_APPROVAL
        if selector == "0x23b872dd":
            return TransactionType.ERC20_TRANSFER
        return TransactionType.CONTRACT_INTERACTION

    def _decode_known(
        self, selector: str, signature: str, contract_address: str, words: list[str]
    ) -> ParsedTransaction:
        try:
            if selector == "0xa9059cbb":  # transfer(address,uint256)
                recipient = decode_address(words[0])
                amount = decode_uint256(words[1])
                return ParsedTransaction(
                    tx_type=TransactionType.ERC20_TRANSFER,
                    decode_status=DecodeStatus.DECODED,
                    contract_address=contract_address,
                    decoded_function=signature,
                    recipient=recipient,
                    token_amount=str(amount),
                    parameters={"recipient": recipient, "amount": str(amount)},
                )

            if selector == "0x095ea7b3":  # approve(address,uint256)
                spender = decode_address(words[0])
                amount = decode_uint256(words[1])
                notes = []
                # 2**256 - 1: the canonical "unlimited approval" sentinel.
                is_unlimited = amount == 2**256 - 1
                if is_unlimited:
                    notes.append("unlimited approval amount (max uint256)")
                return ParsedTransaction(
                    tx_type=TransactionType.ERC20_APPROVAL,
                    decode_status=DecodeStatus.DECODED,
                    contract_address=contract_address,
                    decoded_function=signature,
                    spender=spender,
                    token_amount=str(amount),
                    parameters={"spender": spender, "amount": str(amount)},
                    notes=notes,
                    is_unlimited_approval=is_unlimited,
                )

            if selector == "0x23b872dd":  # transferFrom(address,address,uint256)
                sender = decode_address(words[0])
                recipient = decode_address(words[1])
                amount = decode_uint256(words[2])
                return ParsedTransaction(
                    tx_type=TransactionType.ERC20_TRANSFER,
                    decode_status=DecodeStatus.DECODED,
                    contract_address=contract_address,
                    decoded_function=signature,
                    sender=sender,
                    recipient=recipient,
                    token_amount=str(amount),
                    parameters={"sender": sender, "recipient": recipient, "amount": str(amount)},
                )
        except CalldataDecodeError as exc:
            return ParsedTransaction(
                tx_type=self._type_for_selector(selector),
                decode_status=DecodeStatus.PARTIALLY_DECODED,
                contract_address=contract_address,
                decoded_function=signature,
                notes=[f"parameter decode failed: {exc}"],
            )

        # Unreachable given KNOWN_SELECTORS only contains the three cases
        # above, but never silently fall through to a fabricated result.
        return ParsedTransaction(
            tx_type=TransactionType.CONTRACT_INTERACTION,
            decode_status=DecodeStatus.UNDECODED,
            contract_address=contract_address,
            decoded_function=signature,
            notes=["known selector has no decode implementation"],
        )
