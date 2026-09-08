"""API response schema for wallet endpoints."""
from pydantic import BaseModel


class WalletResponse(BaseModel):
    address: str
    chain: str
    balance_wei: str
    transaction_count: int
    note: str = (
        "Based on public on-chain information only. Risk scoring is not "
        "implemented until Phase 4."
    )
