"""User registration/authentication (product spec section 25).

Syntax-checked only below this docstring — SQLAlchemy isn't installed in
the environment that generated this repo. The password/JWT logic it
calls into (password.py, jwt.py) is genuinely tested (see
tests/test_password.py, tests/test_jwt.py).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password, needs_rehash, verify_password
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    """Deliberately the same error for "no such user" and "wrong
    password" — a login endpoint must not let an attacker distinguish
    which one failed (that would leak which emails are registered)."""


async def register_user(db: AsyncSession, *, email: str, password: str) -> User:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise EmailAlreadyRegisteredError(f"{email} is already registered")

    user = User(email=email, hashed_password=hash_password(password), is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise InvalidCredentialsError("invalid email or password")
    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("invalid email or password")

    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)
        await db.commit()

    return user
