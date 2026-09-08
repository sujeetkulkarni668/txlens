"""GET /api/v1/tokens/{address} — symbol/name/decimals/supply via eth_call
(product spec section 13, honestly scoped — see TokenIntelligenceService)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.blockchain.dependency import get_blockchain_provider
from app.blockchain.provider import BlockchainProvider
from app.intelligence.token_service import TokenIntelligenceService
from app.schemas.intelligence import TokenResponse
from app.validation.evm import ADDRESS_PATH_PATTERN

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.get("/{address}", response_model=TokenResponse)
async def get_token(
    address: Annotated[str, Path(pattern=ADDRESS_PATH_PATTERN)], provider: BlockchainProvider = Depends(get_blockchain_provider)
) -> TokenResponse:
    result = await TokenIntelligenceService(provider).inspect(address)
    return TokenResponse(**result)
