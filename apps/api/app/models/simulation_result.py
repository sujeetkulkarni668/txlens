"""Transaction simulation output (section 10).

Simulation is explicitly distinct from actual blockchain execution and never
claims to guarantee a future outcome.
"""
from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SimulationResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "simulation_results"

    transaction_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), unique=True, nullable=False
    )

    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gas_estimate: Mapped[str | None] = mapped_column(String(78), nullable=True)
    decoded_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    asset_changes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    approvals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    events: Mapped[list | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Explicit unsupported/unknown states — never fabricated (section 34).
    trace_supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="simulation_result")
