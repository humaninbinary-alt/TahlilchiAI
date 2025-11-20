"""Authentication and authorization dependencies."""

from typing import List
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth.jwt_service import JWTService

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Verify and decode token
        payload = JWTService.verify_token(token, token_type="access")
        user_id_raw = payload.get("sub")
        tenant_id_raw = payload.get("tenant_id")
        token_role = payload.get("role")

        if not user_id_raw or not tenant_id_raw:
            raise ValueError("Token missing required claims")

        user_id = UUID(user_id_raw)
        tenant_id = UUID(tenant_id_raw)

    except (JWTError, ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database and enforce tenant isolation
    query = select(User).where(
        User.id == user_id,
        User.tenant_id == tenant_id,
        User.is_active.is_(True),
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_role and user.role.value != token_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token role does not match user role",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.user = user
    request.state.tenant_id = user.tenant_id
    request.state.user_id = user.id

    return user


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: List of roles that are allowed

    Returns:
        Dependency function that checks user role

    Example:
        @router.post("/admin-only")
        async def admin_endpoint(
            user: User = Depends(require_role([UserRole.admin]))
        ):
            ...
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required role."""
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


async def verify_tenant_access(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user),
) -> UUID:
    """
    Verify user has access to the specified tenant.

    Args:
        tenant_id: Tenant ID to verify access to
        current_user: Current authenticated user

    Returns:
        Tenant ID if access is granted

    Raises:
        HTTPException: 403 if user doesn't belong to tenant
    """
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You don't have permission to access this tenant's resources",
        )

    return tenant_id


def get_current_tenant_id(current_user: User = Depends(get_current_user)) -> UUID:
    """
    Get current user's tenant ID from JWT token.

    Args:
        current_user: Current authenticated user

    Returns:
        Tenant UUID
    """
    return current_user.tenant_id


def get_current_user_id(current_user: User = Depends(get_current_user)) -> UUID:
    """
    Get current user's ID.

    Args:
        current_user: Current authenticated user

    Returns:
        User UUID
    """
    return current_user.id
