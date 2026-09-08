"""User-defined security policies (section 18)."""
from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Policy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "policies"

    owner_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g. maximum_transaction_value, maximum_daily_spend, require_review_above,
    # block_unlimited_approvals, block_unknown_contracts, require_review_for_new_contracts
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="policies")
