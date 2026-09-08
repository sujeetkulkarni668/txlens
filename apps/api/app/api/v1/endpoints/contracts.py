"""GET /api/v1/contracts/{address} — bytecode presence/size only (product
spec section 12, honestly scoped — see ContractIntelligenceService)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.blockchain.dependency import get_blockchain_provider
from app.blockchain.provider import BlockchainProvider
from app.intelligence.contract_service import ContractIntelligenceService
from app.schemas.intelligence import ContractResponse
from app.validation.evm import ADDRESS_PATH_PATTERN

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("/{address}", response_model=ContractResponse)
async def get_contract(
    address: Annotated[str, Path(pattern=ADDRESS_PATH_PATTERN)], provider: BlockchainProvider = Depends(get_blockchain_provider)
) -> ContractResponse:
    result = await ContractIntelligenceService(provider).inspect(address)
    return ContractResponse(**result)
