"""API response schemas for contract/token intelligence and mined
transaction lookup."""
from pydantic import BaseModel, Field


class ContractResponse(BaseModel):
    address: str
    is_contract: bool
    bytecode_size_bytes: int
    source_verified: bool | None
    abi: dict | None
    notes: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    address: str
    is_contract: bool
    symbol: str | None
    name: str | None
    decimals: int | None
    total_supply: str | None
    notes: list[str] = Field(default_factory=list)


class TransactionLookupResponse(BaseModel):
    found: bool
    hash: str
    from_address: str | None = None
    to_address: str | None = None
    value: str | None = None
    block_number: int | None = None
    status: bool | None = None  # from receipt; None if not yet mined/no receipt
    gas_used: int | None = None
