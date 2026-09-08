"""Public EVM wallet records TxLens has analyzed.

Only public, on-chain-derived attributes are stored — never private keys or
seed phrases.
"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Wallet(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "wallets"

    address: Mapped[str] = mapped_column(String(42), unique=True, index=True, nullable=False)
    chain: Mapped[str] = mapped_column(String(64), nullable=False, default="base-sepolia")

    # Cached public intelligence signals (section 11). Populated by the
    # wallet-intelligence service in a later phase.
    first_seen_block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transaction_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    risk_scores: Mapped[list["RiskScore"]] = relationship(back_populates="wallet")
