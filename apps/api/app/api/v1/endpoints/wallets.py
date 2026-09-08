"""GET /api/v1/wallets/{address} — Phase 2 scope: public balance + nonce
only, via BlockchainProvider. Wallet risk intelligence (section 11 —
transaction history, contract interactions, age, risk signals) is added in
Phase 4 alongside the ML risk engine; GET /wallets/{address}/risk is
introduced then rather than stubbed here.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.blockchain.dependency import get_blockchain_provider
from app.blockchain.provider import BlockchainProvider
from app.validation.evm import ADDRESS_PATH_PATTERN
from app.core.config import get_settings
from app.schemas.wallet import WalletResponse

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{address}", response_model=WalletResponse)
async def get_wallet(
    address: Annotated[str, Path(pattern=ADDRESS_PATH_PATTERN)], provider: BlockchainProvider = Depends(get_blockchain_provider)
) -> WalletResponse:
    settings = get_settings()
    balance = await provider.get_balance(address)
    tx_count = await provider.get_transaction_count(address)
    return WalletResponse(
        address=address,
        chain=settings.evm_chain,
        balance_wei=str(balance),
        transaction_count=tx_count,
    )
