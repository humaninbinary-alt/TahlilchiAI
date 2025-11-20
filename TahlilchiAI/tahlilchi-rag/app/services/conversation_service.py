"""Service for managing conversations and messages."""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Service for managing conversations and messages.

    Responsibilities:
    - Create and manage conversation threads
    - Add messages to conversations
    - Retrieve conversation history
    - Build conversation context for LLM
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize conversation service.

        Args:
            db: Database session for operations
        """
        self.db = db
        self.logger = logger

    async def create_conversation(
        self,
        tenant_id: UUID,
        chat_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
    ) -> Conversation:
        """
        Create a new conversation thread.

        Args:
            tenant_id: Tenant UUID for isolation
            chat_id: Parent chat UUID
            user_id: User who owns this conversation
            title: Optional conversation title

        Returns:
            Created conversation
        """
        conversation = Conversation(
            tenant_id=tenant_id,
            chat_id=chat_id,
            user_id=user_id,
            title=title or "New Conversation",
        )

        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)

        self.logger.info(f"Created conversation {conversation.id} for chat {chat_id}")
        return conversation

    async def get_conversation(
        self, conversation_id: UUID, tenant_id: UUID
    ) -> Optional[Conversation]:
        """
        Get a conversation by ID.

        Args:
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            Conversation if found, None otherwise
        """
        query = select(Conversation).where(
            Conversation.id == conversation_id, Conversation.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        tenant_id: UUID,
        chat_id: UUID,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Conversation], int]:
        """
        List conversations for a chat with pagination.

        Args:
            tenant_id: Tenant UUID for isolation
            chat_id: Parent chat UUID
            user_id: Optional user filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (conversations list, total count)
        """
        # Build query
        query = select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.chat_id == chat_id,
            Conversation.is_active.is_(True),
        )

        if user_id:
            query = query.where(Conversation.user_id == user_id)

        query = query.order_by(desc(Conversation.updated_at))
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await self.db.execute(query)
        conversations = list(result.scalars().all())

        # Get total count
        count_query = select(func.count(Conversation.id)).where(
            Conversation.tenant_id == tenant_id,
            Conversation.chat_id == chat_id,
            Conversation.is_active.is_(True),
        )

        if user_id:
            count_query = count_query.where(Conversation.user_id == user_id)

        total = await self.db.scalar(count_query) or 0

        return conversations, total

    async def add_message(
        self,
        conversation_id: UUID,
        tenant_id: UUID,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID for isolation
            role: Message role (user/assistant/system)
            content: Message text content
            metadata: Optional metadata for assistant messages

        Returns:
            Created message
        """
        message = Message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
        )

        # Set metadata if provided (for assistant messages)
        if metadata:
            message.retrieval_mode = metadata.get("retrieval_mode")
            message.contexts_used = metadata.get("contexts_used")
            message.confidence = metadata.get("confidence")
            message.citations = metadata.get("citations")
            message.retrieval_time_ms = metadata.get("retrieval_time_ms")
            message.generation_time_ms = metadata.get("generation_time_ms")
            message.metadata_json = metadata.get("extra", {})

        self.db.add(message)

        # Update conversation updated_at timestamp
        query = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()

        if conversation:
            conversation.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(message)

        self.logger.info(f"Added {role} message to conversation {conversation_id}")
        return message

    async def get_conversation_history(
        self,
        conversation_id: UUID,
        tenant_id: UUID,
        limit: Optional[int] = None,
    ) -> list[Message]:
        """
        Get message history for a conversation.

        Args:
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID for isolation
            limit: Optional limit for recent N messages

        Returns:
            List of messages in chronological order
        """
        query = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_id,
        )

        if limit:
            # Get last N messages (most recent first, then reverse)
            query = query.order_by(desc(Message.created_at)).limit(limit)
            result = await self.db.execute(query)
            messages = list(reversed(result.scalars().all()))
        else:
            # Get all messages in chronological order
            query = query.order_by(Message.created_at)
            result = await self.db.execute(query)
            messages = list(result.scalars().all())

        return messages

    async def get_conversation_context(
        self, conversation_id: UUID, tenant_id: UUID, last_n: int = 5
    ) -> list[dict[str, str]]:
        """
        Get recent conversation context for multi-turn queries.

        Args:
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID for isolation
            last_n: Number of recent exchanges to include

        Returns:
            List of message dicts: [{"role": "user", "content": "..."}, ...]
        """
        # Get last N*2 messages (N exchanges = N user + N assistant)
        messages = await self.get_conversation_history(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            limit=last_n * 2,
        )

        # Format for LLM context
        context = []
        for msg in messages:
            context.append({"role": msg.role, "content": msg.content})

        return context

    async def delete_conversation(self, conversation_id: UUID, tenant_id: UUID) -> bool:
        """
        Soft delete a conversation.

        Args:
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            True if deleted, False if not found
        """
        query = select(Conversation).where(
            Conversation.id == conversation_id, Conversation.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return False

        conversation.is_active = False
        await self.db.commit()

        self.logger.info(f"Deleted conversation {conversation_id}")
        return True
