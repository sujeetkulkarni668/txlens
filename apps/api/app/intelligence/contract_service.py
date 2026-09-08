"""Contract intelligence (product spec section 12) — scoped honestly to
what a plain RPC endpoint provides: bytecode presence/size. Source
verification, ABI, function selectors beyond what the parser already
decodes, and ownership/admin-function detection all require a
verified-source database (an explorer API) this phase doesn't integrate.
"""
from __future__ import annotations

from app.blockchain.provider import BlockchainProvider


class ContractIntelligenceService:
    def __init__(self, provider: BlockchainProvider):
        self._provider = provider

    async def inspect(self, address: str) -> dict:
        code = await self._provider.get_code(address)
        is_contract = code != "0x"
        return {
            "address": address,
            "is_contract": is_contract,
            "bytecode_size_bytes": (len(code) - 2) // 2 if is_contract else 0,
            "source_verified": None,
            "abi": None,
            "notes": (
                [
                    "source verification, ABI, and admin-function detection require an "
                    "explorer/indexer integration — not implemented this phase; "
                    "source_verified is honestly reported as unknown (null), not assumed false"
                ]
                if is_contract
                else ["address has no code — this is an externally-owned account, not a contract"]
            ),
        }
