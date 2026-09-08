"""Smart contract intelligence records (section 12).

Verification/ABI/bytecode availability is tracked explicitly per field —
unverified contracts are represented honestly, never guessed.
"""
from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Contract(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "contracts"

    address: Mapped[str] = mapped_column(String(42), unique=True, index=True, nullable=False)
    chain: Mapped[str] = mapped_column(String(64), nullable=False, default="base-sepolia")

    source_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    abi: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    abi_inferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bytecode_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    deployed_block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    function_selectors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    admin_functions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    risk_scores: Mapped[list["RiskScore"]] = relationship(back_populates="contract")
