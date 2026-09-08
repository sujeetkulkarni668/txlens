"""Top-level /api/v1 router.

Endpoints are added phase by phase as their backing services land (see
docs/roadmap.md). Each router below is real, wired service logic — never a
stub route returning fake data.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.contracts import router as contracts_router
from app.api.v1.endpoints.policies import router as policies_router
from app.api.v1.endpoints.simulation import router as simulation_router
from app.api.v1.endpoints.tokens import router as tokens_router
from app.api.v1.endpoints.transaction_lookup import router as transaction_lookup_router
from app.api.v1.endpoints.transactions import router as transactions_router
from app.api.v1.endpoints.wallets import router as wallets_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(transactions_router)
router.include_router(simulation_router)
router.include_router(transaction_lookup_router)
router.include_router(wallets_router)
router.include_router(policies_router)
router.include_router(contracts_router)
router.include_router(tokens_router)
