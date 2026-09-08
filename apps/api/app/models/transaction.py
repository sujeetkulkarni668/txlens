"""Transactions submitted to TxLens for analysis (pre- or post-signature)."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transactions"

    chain: Mapped[str] = mapped_column(String(64), nullable=False, default="base-sepolia")
    tx_hash: Mapped[str | None] = mapped_column(String(66), unique=True, nullable=True, index=True)

    from_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    to_address: Mapped[str | None] = mapped_column(String(42), nullable=True, index=True)
    value_wei: Mapped[str] = mapped_column(String(78), nullable=False, default="0")
    data: Mapped[str | None] = mapped_column(String, nullable=True)

    # Populated by the transaction parser (section 8): native_transfer,
    # erc20_transfer, erc20_approval, contract_interaction, unknown.
    tx_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")

    # Set once actually submitted on-chain by the user's wallet (section 20).
    submitted: Mapped[bool] = mapped_column(default=False, nullable=False)

    analysis: Mapped["TransactionAnalysis | None"] = relationship(
        back_populates="transaction", uselist=False
    )
    simulation_result: Mapped["SimulationResult | None"] = relationship(
        back_populates="transaction", uselist=False
    )
