"""POST /api/v1/auth/register, POST /api/v1/auth/login (product spec
section 25). Rate-limited: auth endpoints are the classic brute-force
target, and this is public/unauthenticated by definition so it needs its
own protection independent of the get_current_user_id dependency.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import EmailAlreadyRegisteredError, InvalidCredentialsError, authenticate_user, register_user
from app.auth.tokens import ACCESS_TOKEN_TTL_SECONDS, create_access_token
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:
    try:
        user = await register_user(db, email=body.email, password=body.password)
    except EmailAlreadyRegisteredError:
        # Deliberately vague — "email already registered" is itself a
        # user-enumeration leak, but registration UX conventionally
        # accepts that trade-off (unlike login, see auth/service.py).
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    return UserResponse(id=str(user.id), email=user.email, is_active=user.is_active)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        user = await authenticate_user(db, email=body.email, password=body.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, expires_in=ACCESS_TOKEN_TTL_SECONDS)
