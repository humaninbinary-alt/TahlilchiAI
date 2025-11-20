"""Pydantic schemas for conversation and message API contracts."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Request to send a message."""

    content: str = Field(
        ..., min_length=1, max_length=5000, description="Message content"
    )


class MessageResponse(BaseModel):
    """Single message in conversation."""

    id: UUID
    role: str
    content: str
    created_at: datetime

    # Assistant message metadata
    retrieval_mode: Optional[str] = None
    contexts_used: Optional[int] = None
    confidence: Optional[str] = None
    citations: Optional[list[dict[str, Any]]] = None

    # Performance metrics
    retrieval_time_ms: Optional[int] = None
    generation_time_ms: Optional[int] = None

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Conversation summary without messages."""

    id: UUID
    chat_id: UUID
    user_id: UUID
    title: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """Conversation with full message history."""

    conversation: ConversationResponse
    messages: list[MessageResponse]
    total_messages: int


class ConversationListResponse(BaseModel):
    """List of conversations with pagination."""

    conversations: list[ConversationResponse]
    total: int
