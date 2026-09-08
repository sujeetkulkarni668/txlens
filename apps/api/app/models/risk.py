"""ML risk engine output (section 14): score, level, and feature signals."""
from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RiskScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "risk_scores"

    # A risk score can be attached to a wallet, a contract, or a transaction
    # analysis — exactly one of these should be set per row.
    wallet_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=True
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )

    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)  # LOW|MEDIUM|HIGH|CRITICAL

    # Whether this score came from a model trained on synthetic/demo data —
    # must be surfaced to the user, never hidden (section 14).
    model_is_demo_data: Mapped[bool] = mapped_column(default=True, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    wallet: Mapped["Wallet | None"] = relationship(back_populates="risk_scores")
    contract: Mapped["Contract | None"] = relationship(back_populates="risk_scores")
    signals: Mapped[list["RiskSignal"]] = relationship(back_populates="risk_score")


class RiskSignal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "risk_signals"

    risk_score_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_scores.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    risk_score: Mapped["RiskScore"] = relationship(back_populates="signals")
