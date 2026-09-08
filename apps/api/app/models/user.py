"""Authenticated TxLens users (MVP auth — see section 25 of the product spec).

Never store private keys or seed phrases here. `wallet_address` (optional) is
used only for signed-message wallet-ownership verification, not custody.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional: address the user has proven ownership of via signed message.
    verified_wallet_address: Mapped[str | None] = mapped_column(String(42), nullable=True)

    policies: Mapped[list["Policy"]] = relationship(back_populates="owner")
    security_reports: Mapped[list["SecurityReport"]] = relationship(back_populates="owner")
