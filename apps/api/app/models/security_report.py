"""Readable investigation reports (section 22 "Reports" screen)."""
from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SecurityReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "security_reports"

    owner_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transaction_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    structured_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="security_reports")
