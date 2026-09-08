"""POST /api/v1/transactions/simulate (product spec section 10)."""
from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_simulation_service
from app.schemas.common import TransactionInput
from app.schemas.simulation import SimulationResponse
from app.simulation.service import SimulationService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_transaction(
    request: TransactionInput,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationResponse:
    result = await service.simulate(
        chain=request.chain,
        from_address=request.from_address,
        to=request.to,
        value=request.value,
        data=request.data,
    )
    return SimulationResponse(**result.__dict__)
