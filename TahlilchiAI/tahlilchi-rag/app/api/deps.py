"""API Dependencies - Improved database session management."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db
from app.models.chat import Chat
from app.models.chat_access import ChatAccess
from app.models.tenant import Tenant
from app.models.user import User, UserRole


async def get_current_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Get and validate tenant."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found or inactive",
        )

    return tenant


async def get_user_by_id(
    user_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Fetch a user by id while enforcing tenant isolation."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found or inactive",
        )

    return user


async def get_chat_with_access(
    chat_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
    user: Optional[User] = None,
) -> Chat:
    """Get chat and verify access permissions."""
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.tenant_id == tenant_id,
            Chat.is_active.is_(True),
        )
    )
    chat = result.scalar_one_or_none()

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat {chat_id} not found or inactive",
        )

    if user:
        await _ensure_user_can_access_chat(chat=chat, user=user, db=db)

    return chat


async def _ensure_user_can_access_chat(
    chat: Chat,
    user: User,
    db: AsyncSession,
) -> None:
    """Raise if user cannot access the chat."""
    if user.tenant_id != chat.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat belongs to a different tenant",
        )

    if user.role in {UserRole.admin, UserRole.manager}:
        return

    result = await db.execute(
        select(ChatAccess.id).where(
            ChatAccess.chat_id == chat.id,
            ChatAccess.user_id == user.id,
            ChatAccess.tenant_id == chat.tenant_id,
        )
    )

    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this chat",
        )


async def get_current_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Chat:
    """Convenience dependency to fetch chat with access enforcement."""
    return await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )


class TransactionalSession:
    """
    Context manager for explicit transaction control.

    Usage:
        async with TransactionalSession(db) as session:
            # Do multiple operations
            await session.execute(...)
            await session.execute(...)
            # Commit happens on successful exit
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._committed = False

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Rollback on exception
            await self.session.rollback()
        elif not self._committed:
            # Commit on success
            await self.session.commit()
            self._committed = True

        # Return False to propagate any exception
        return False

    async def commit(self):
        """Explicit commit."""
        await self.session.commit()
        self._committed = True

    async def rollback(self):
        """Explicit rollback."""
        await self.session.rollback()
