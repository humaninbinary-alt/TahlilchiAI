"""Pydantic schemas for authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1, max_length=255)
    tenant_id: UUID


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response (no password)."""

    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Login response with tokens and user data."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
