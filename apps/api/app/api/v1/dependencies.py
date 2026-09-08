"""Shared FastAPI dependency providers for the v1 API."""
from functools import lru_cache

from fastapi import Depends

from app.auth.dependency import get_current_user_id
from app.blockchain.dependency import get_blockchain_provider
from app.blockchain.provider import BlockchainProvider
from app.parser.parser import TransactionParser
from app.simulation.service import SimulationService

# Phase 11: get_current_user_id is now real JWT-verified authentication
# (app/auth/dependency.py) — re-exported here under the same name it had
# as a Phase 5 hardcoded placeholder, so every existing call site
# (transactions.py, policies.py) picked up real auth with no changes
# needed there. Import it from here for consistency with the rest of
# this module, not directly from app.auth.dependency.
__all__ = [
    "get_simulation_service",
    "get_risk_engine_service",
    "get_policy_engine",
    "get_ai_analyst_service",
    "get_current_user_id",
]


def get_simulation_service(
    provider: BlockchainProvider = Depends(get_blockchain_provider),
) -> SimulationService:
    return SimulationService(provider, TransactionParser())


@lru_cache
def _cached_risk_engine_service():
    # Imported lazily so apps/api can still start up (and every other
    # endpoint keep working) even in a local dev setup where
    # PYTHONPATH doesn't yet include ml/ and services/risk-engine/ — see
    # README "Local setup" for the required PYTHONPATH. The error raised
    # here on first use is far clearer than an import failure at app
    # startup would be.
    from risk_engine.model import RiskModel
    from risk_engine.service import RiskEngineService

    model = RiskModel.load(model_version="risk-model-v1-synthetic")
    return RiskEngineService(model)


def get_risk_engine_service():
    return _cached_risk_engine_service()


def get_policy_engine():
    from app.policy.engine import PolicyEngine

    return PolicyEngine()


@lru_cache
def _cached_ai_analyst_service():
    """Returns None (not an error) when AI_API_KEY isn't configured — the
    analyze endpoint treats a missing AI stage as "skipped", never as a
    request failure, since AI is one stage of several in the pipeline."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.ai_api_key:
        return None

    from ai_analyst.factory import get_ai_provider
    from ai_analyst.service import AIAnalystService

    provider = get_ai_provider(
        provider_name=settings.ai_provider, api_key=settings.ai_api_key, model=settings.ai_model
    )
    return AIAnalystService(provider)


def get_ai_analyst_service():
    return _cached_ai_analyst_service()
