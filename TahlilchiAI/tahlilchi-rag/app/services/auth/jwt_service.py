"""JWT token service for authentication."""

from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import UUID

from jose import JWTError, jwt

from app.config import settings


class JWTService:
    """Service for creating and verifying JWT tokens."""

    @staticmethod
    def create_access_token(user_id: UUID, tenant_id: UUID, role: str) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            role: User role (admin/manager/member)

        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return token

    @staticmethod
    def create_refresh_token(user_id: UUID) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: User UUID

        Returns:
            JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return token

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type (access/refresh)

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid or expired
            ValueError: If token type doesn't match
        """
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise ValueError(f"Invalid token type. Expected {token_type}")

            return payload

        except JWTError as e:
            raise JWTError(f"Invalid token: {str(e)}")

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode JWT token without verification (use carefully).

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token cannot be decoded
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_signature": False},
            )
            return payload
        except JWTError as e:
            raise JWTError(f"Cannot decode token: {str(e)}")
