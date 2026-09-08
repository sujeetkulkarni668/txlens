"""ERC-20 (and future token-standard) intelligence records (section 13)."""
from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Token(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tokens"

    address: Mapped[str] = mapped_column(String(42), unique=True, index=True, nullable=False)
    chain: Mapped[str] = mapped_column(String(64), nullable=False, default="base-sepolia")

    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decimals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_supply: Mapped[str | None] = mapped_column(String(78), nullable=True)

    contract_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_indicators: Mapped[list | None] = mapped_column(JSON, nullable=True)
