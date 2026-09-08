"""Token intelligence (product spec section 13) — scoped to what's
honestly derivable from raw eth_call reads: symbol, name, decimals,
total supply. Verification status, holder distribution, and risk
indicators are NOT included: they require an indexer/explorer, which
this phase doesn't have.
"""
from __future__ import annotations

from app.blockchain.erc20_calls import (
    DECIMALS_SELECTOR,
    NAME_SELECTOR,
    SYMBOL_SELECTOR,
    TOTAL_SUPPLY_SELECTOR,
    decode_string_return,
    decode_uint_return,
)
from app.blockchain.exceptions import BlockchainProviderError
from app.blockchain.provider import BlockchainProvider


class TokenIntelligenceService:
    def __init__(self, provider: BlockchainProvider):
        self._provider = provider

    async def inspect(self, address: str) -> dict:
        code = await self._provider.get_code(address)
        is_contract = code != "0x"

        result: dict = {
            "address": address,
            "is_contract": is_contract,
            "symbol": None,
            "name": None,
            "decimals": None,
            "total_supply": None,
            "notes": [],
        }
        if not is_contract:
            result["notes"].append("address has no code — not a token contract")
            return result

        result["symbol"] = await self._safe_string_call(address, SYMBOL_SELECTOR, "symbol")
        result["name"] = await self._safe_string_call(address, NAME_SELECTOR, "name")
        result["decimals"] = await self._safe_uint_call(address, DECIMALS_SELECTOR, "decimals")
        result["total_supply"] = await self._safe_uint_call(
            address, TOTAL_SUPPLY_SELECTOR, "totalSupply", as_str=True
        )
        result["notes"].append(
            "verification status, holder distribution, and risk indicators require an "
            "indexer/explorer integration — not implemented this phase"
        )
        return result

    async def _safe_string_call(self, address: str, selector: str, field: str) -> str | None:
        try:
            call_result = await self._provider.call(to=address, data=selector)
        except BlockchainProviderError:
            return None
        if not call_result.success or call_result.return_data is None:
            return None
        return decode_string_return(call_result.return_data)

    async def _safe_uint_call(
        self, address: str, selector: str, field: str, *, as_str: bool = False
    ):
        try:
            call_result = await self._provider.call(to=address, data=selector)
        except BlockchainProviderError:
            return None
        if not call_result.success or call_result.return_data is None:
            return None
        value = decode_uint_return(call_result.return_data)
        if value is None:
            return None
        return str(value) if as_str else value
