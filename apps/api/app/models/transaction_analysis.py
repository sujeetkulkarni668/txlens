"""Full analysis record for a transaction: parser + AI output (section 15).

This is the row rendered by GET /api/v1/transactions/{hash} and referenced
by security reports. ML risk and policy results live in their own tables
(RiskScore, Policy evaluation) and are joined at read time.
"""
from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TransactionAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transaction_analysis"

    transaction_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), unique=True, nullable=False
    )

    # Parser output (section 8).
    decoded_function: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decoded_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # AI analyst structured output (section 15).
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_risk_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_potential_impact: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ALLOW|REVIEW|BLOCK
    ai_confidence: Mapped[int | None] = mapped_column(nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="analysis")
