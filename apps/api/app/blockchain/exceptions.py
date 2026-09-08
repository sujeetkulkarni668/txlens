"""Exceptions for the blockchain provider layer."""


class BlockchainProviderError(Exception):
    """Base class for all blockchain provider errors."""


class RpcError(BlockchainProviderError):
    """The RPC endpoint returned a JSON-RPC error object."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"RPC error {code}: {message}")


class RpcTransportError(BlockchainProviderError):
    """The RPC endpoint could not be reached, or returned a non-JSON /
    non-2xx response."""


class UnsupportedCapabilityError(BlockchainProviderError):
    """The requested capability is not supported by this provider/network.

    Raised rather than silently returning a fabricated result — callers
    (simulation, MCP tools) must surface this as an explicit
    "unsupported" state (product spec sections 17 and 34).
    """
