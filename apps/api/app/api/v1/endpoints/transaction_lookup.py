"""GET /api/v1/transactions/{hash} — looks up a mined (or pending)
transaction by hash via BlockchainProvider (product spec section 7)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.blockchain.dependency import get_blockchain_provider
from app.blockchain.provider import BlockchainProvider
from app.schemas.intelligence import TransactionLookupResponse
from app.validation.evm import TX_HASH_PATH_PATTERN

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/{tx_hash}", response_model=TransactionLookupResponse)
async def get_transaction(
    tx_hash: Annotated[str, Path(pattern=TX_HASH_PATH_PATTERN)], provider: BlockchainProvider = Depends(get_blockchain_provider)
) -> TransactionLookupResponse:
    tx = await provider.get_transaction(tx_hash)
    if tx is None:
        return TransactionLookupResponse(found=False, hash=tx_hash)

    receipt = await provider.get_transaction_receipt(tx_hash)
    return TransactionLookupResponse(
        found=True,
        hash=tx.hash,
        from_address=tx.from_address,
        to_address=tx.to_address,
        value=tx.value,
        block_number=tx.block_number,
        status=receipt.status if receipt else None,
        gas_used=receipt.gas_used if receipt else None,
    )
