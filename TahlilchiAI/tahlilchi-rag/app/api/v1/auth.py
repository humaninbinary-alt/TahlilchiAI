"""Authentication API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.core.security import hash_password, validate_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import (LoginResponse, TokenRefresh, TokenResponse,
                              UserLogin, UserRegister, UserResponse)
from app.services.auth.jwt_service import JWTService

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _get_tenant(db: AsyncSession, tenant_id: UUID) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user within a tenant."""
    is_valid, error = validate_password(payload.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    tenant = await _get_tenant(db, payload.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = await db.execute(
        select(User).where(
            User.email == payload.email, User.tenant_id == payload.tenant_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="User with this email already exists in the tenant"
        )

    user = User(
        tenant_id=payload.tenant_id,
        email=payload.email,
        full_name=payload.full_name,
        role=UserRole.member,
    )
    user.set_password(payload.password)

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and issue tokens."""
    user = await _get_user_by_email(db, payload.email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    await db.commit()

    access = JWTService.create_access_token(user.id, user.tenant_id, user.role.value)
    refresh = JWTService.create_refresh_token(user.id)

    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh access token."""
    try:
        token_data = JWTService.verify_token(payload.refresh_token, token_type="refresh")
    except Exception as exc:  # pragma: no cover - passlib errors already handled
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    user_id = token_data.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access = JWTService.create_access_token(user.id, user.tenant_id, user.role.value)
    new_refresh = JWTService.create_refresh_token(user.id)

    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Return current authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(_: User = Depends(get_current_user)) -> dict[str, str]:
    """
    Logout endpoint (stateless JWTs cannot be revoked server-side).

    Returns:
        Simple acknowledgement response.
    """
    return {"status": "success"}

