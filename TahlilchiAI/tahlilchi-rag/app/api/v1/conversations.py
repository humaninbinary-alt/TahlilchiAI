"""API endpoints for conversation management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_chat_with_access, get_db
from app.core.auth import get_current_user
from app.models.user import User, UserRole
from app.schemas.conversation import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/chats/{chat_id}/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    chat_id: UUID,
    title: Optional[str] = Query(None, description="Conversation title"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    """
    Create a new conversation thread.

    Args:
        chat_id: Parent chat UUID
        tenant_id: Tenant UUID for isolation
        user_id: User UUID who owns the conversation
        title: Optional conversation title
        db: Database session

    Returns:
        Created conversation
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    service = ConversationService(db)

    conversation = await service.create_conversation(
        tenant_id=current_user.tenant_id,
        chat_id=chat_id,
        user_id=current_user.id,
        title=title,
    )

    # Add message count
    response = ConversationResponse.model_validate(conversation)
    response.message_count = len(conversation.messages)

    return response


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    chat_id: UUID,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationListResponse:
    """
    List all conversations for a chat.

    Args:
        chat_id: Parent chat UUID
        tenant_id: Tenant UUID for isolation
        user_id: Optional user filter
        skip: Pagination offset
        limit: Pagination limit
        db: Database session

    Returns:
        List of conversations with total count
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    owner_filter: Optional[UUID] = None
    if current_user.role == UserRole.member:
        owner_filter = current_user.id
    elif user_id:
        owner_filter = user_id

    service = ConversationService(db)

    conversations, total = await service.list_conversations(
        tenant_id=current_user.tenant_id,
        chat_id=chat_id,
        user_id=owner_filter,
        skip=skip,
        limit=limit,
    )

    # Add message counts
    conversation_responses = []
    for conv in conversations:
        response = ConversationResponse.model_validate(conv)
        response.message_count = len(conv.messages)
        conversation_responses.append(response)

    return ConversationListResponse(conversations=conversation_responses, total=total)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    chat_id: UUID,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    """
    Get conversation with full message history.

    Args:
        chat_id: Parent chat UUID
        conversation_id: Conversation UUID
        tenant_id: Tenant UUID for isolation
        db: Database session

    Returns:
        Conversation with all messages

    Raises:
        HTTPException: 404 if conversation not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    service = ConversationService(db)

    conversation = await service.get_conversation(
        conversation_id, current_user.tenant_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.role == UserRole.member and conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Conversation belongs to another user"
        )

    # Get messages
    messages = await service.get_conversation_history(
        conversation_id, current_user.tenant_id
    )

    # Build response
    conv_response = ConversationResponse.model_validate(conversation)
    conv_response.message_count = len(messages)

    return ConversationDetailResponse(
        conversation=conv_response,
        messages=[msg for msg in messages],  # Pydantic will validate
        total_messages=len(messages),
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    chat_id: UUID,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a conversation (soft delete).

    Args:
        chat_id: Parent chat UUID
        conversation_id: Conversation UUID
        tenant_id: Tenant UUID for isolation
        db: Database session

    Raises:
        HTTPException: 404 if conversation not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    service = ConversationService(db)

    if current_user.role == UserRole.member:
        conversation = await service.get_conversation(
            conversation_id, current_user.tenant_id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Conversation belongs to another user"
            )

    success = await service.delete_conversation(conversation_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return None
