"""FastAPI dependency providing a configured BlockchainProvider.

Single place where the concrete provider implementation is chosen — swap
EVMRPCProvider for another implementation here without touching callers.
"""
from functools import lru_cache

from app.blockchain.evm_rpc_provider import EVMRPCProvider
from app.blockchain.provider import BlockchainProvider
from app.core.config import get_settings


@lru_cache
def _cached_provider() -> BlockchainProvider:
    settings = get_settings()
    return EVMRPCProvider(rpc_url=settings.evm_rpc_url)


def get_blockchain_provider() -> BlockchainProvider:
    return _cached_provider()


def get_transaction_parser():
    from app.parser.parser import TransactionParser

    return TransactionParser()
