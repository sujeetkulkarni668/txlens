"""Shared request envelope used by both /transactions/analyze and
/transactions/simulate (product spec sections 7 and 10 use the same shape).

Validators here are the API-boundary enforcement of product spec section
26 ("input validation") — malformed addresses/calldata/values are
rejected with a 422 before they ever reach the parser/simulation/RPC
layer, rather than being silently coerced or causing a confusing error
several layers deep.
"""
from pydantic import BaseModel, Field, field_validator

from app.validation.evm import is_valid_decimal_string, is_valid_evm_address, is_valid_hex_data


class TransactionInput(BaseModel):
    chain: str = "base-sepolia"
    from_address: str = Field(alias="from")
    to: str | None = None
    value: str = "0"
    data: str | None = None

    model_config = {"populate_by_name": True}

    @field_validator("from_address")
    @classmethod
    def validate_from_address(cls, v: str) -> str:
        if not is_valid_evm_address(v):
            raise ValueError(f"'from' is not a valid EVM address: {v!r}")
        return v

    @field_validator("to")
    @classmethod
    def validate_to_address(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_evm_address(v):
            raise ValueError(f"'to' is not a valid EVM address: {v!r}")
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        if not is_valid_decimal_string(v):
            raise ValueError(f"'value' must be a non-negative base-10 integer string, got {v!r}")
        return v

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_hex_data(v):
            raise ValueError(f"'data' must be '0x' followed by whole bytes, got {v!r}")
        return v
