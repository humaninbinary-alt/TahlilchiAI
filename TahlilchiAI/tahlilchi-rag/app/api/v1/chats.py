"""Chat configuration API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_chat_with_access, get_db
from app.core.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.chat import (
    ChatCreateRequest,
    ChatListResponse,
    ChatResponse,
    ChatUpdateRequest,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(
    data: ChatCreateRequest,
    current_user: User = Depends(require_role([UserRole.admin, UserRole.manager])),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new custom chat assistant.

    This endpoint creates a new chat configuration with auto-configured RAG settings
    based on the provided purpose, sensitivity, and language preferences.

    Args:
        data: Chat configuration data
        current_user: Authenticated user (provides tenant isolation)
        db: Database session

    Returns:
        ChatResponse: Created chat configuration
    """
    service = ChatService(db)
    chat = await service.create_chat(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        data=data,
    )
    return ChatResponse.model_validate(chat)


@router.get("", response_model=ChatListResponse)
async def list_chats(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=100, description="Maximum number of records to return"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all chats for the current tenant.

    Returns a paginated list of all active chats for the specified tenant.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user
        db: Database session

    Returns:
        ChatListResponse: List of chats and total count
    """
    service = ChatService(db)
    restrict_to_user = current_user.id if current_user.role == UserRole.member else None
    chats, total = await service.list_chats(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
        restrict_to_user=restrict_to_user,
    )
    return ChatListResponse(
        chats=[ChatResponse.model_validate(c) for c in chats], total=total
    )


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific chat configuration.

    Retrieves detailed configuration for a single chat with tenant isolation.

    Args:
        chat_id: Chat ID to retrieve
        current_user: Authenticated user
        db: Database session

    Returns:
        ChatResponse: Chat configuration

    Raises:
        HTTPException: 404 if chat not found
    """
    chat = await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )
    return ChatResponse.model_validate(chat)


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: UUID,
    data: ChatUpdateRequest,
    current_user: User = Depends(require_role([UserRole.admin, UserRole.manager])),
    db: AsyncSession = Depends(get_db),
):
    """
    Update chat configuration.

    Updates one or more fields of a chat configuration. All fields are optional.

    Args:
        chat_id: Chat ID to update
        data: Update data (partial)
        current_user: Authenticated user
        db: Database session

    Returns:
        ChatResponse: Updated chat configuration

    Raises:
        HTTPException: 404 if chat not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    service = ChatService(db)
    chat = await service.update_chat(current_user.tenant_id, chat_id, data)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatResponse.model_validate(chat)


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: UUID,
    current_user: User = Depends(require_role([UserRole.admin, UserRole.manager])),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete (deactivate) a chat.

    Performs a soft delete by setting is_active to False.

    Args:
        chat_id: Chat ID to delete
        current_user: Authenticated user
        db: Database session

    Returns:
        None: 204 No Content on success

    Raises:
        HTTPException: 404 if chat not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    service = ChatService(db)
    success = await service.delete_chat(current_user.tenant_id, chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return None
