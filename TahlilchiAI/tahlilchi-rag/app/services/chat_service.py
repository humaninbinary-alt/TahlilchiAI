"""Business logic for chat configuration management."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import generate_slug
from app.models.chat import Chat
from app.models.chat_access import ChatAccess
from app.schemas.chat import ChatCreateRequest, ChatUpdateRequest


class ChatService:
    """Business logic for chat configuration management."""

    def __init__(self, db: AsyncSession):
        """
        Initialize ChatService.

        Args:
            db: Async database session
        """
        self.db = db

    async def create_chat(
        self, tenant_id: UUID, user_id: UUID, data: ChatCreateRequest
    ) -> Chat:
        """
        Create a new chat with auto-configuration based on settings.

        Args:
            tenant_id: Tenant ID for isolation
            user_id: User ID who is creating the chat
            data: Chat creation request data

        Returns:
            Chat: Created chat instance
        """
        # Generate slug from name
        slug = generate_slug(data.name)

        # Ensure slug is unique within tenant
        slug = await self._ensure_unique_slug(tenant_id, slug)

        # Auto-configure RAG settings if not provided
        rag_config = self._auto_configure_rag_settings(
            purpose=data.purpose,
            sensitivity=data.sensitivity,
            document_languages=data.document_languages,
        )

        # Create Chat model instance
        chat = Chat(
            tenant_id=tenant_id,
            created_by=user_id,
            name=data.name,
            slug=slug,
            purpose=data.purpose,
            target_audience=data.target_audience,
            tone=data.tone,
            strictness=data.strictness,
            sensitivity=data.sensitivity,
            document_types=data.document_types,
            document_languages=data.document_languages,
            # Use provided values or auto-configured defaults
            embedding_model=data.embedding_model or rag_config["embedding_model"],
            llm_model=data.llm_model or rag_config["llm_model"],
            retrieval_strategy=data.retrieval_strategy
            or rag_config["retrieval_strategy"],
            max_context_chunks=data.max_context_chunks
            or rag_config["max_context_chunks"],
        )

        # Save to database
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)

        return chat

    async def get_chat(self, tenant_id: UUID, chat_id: UUID) -> Optional[Chat]:
        """
        Get a single chat with tenant isolation.

        Args:
            tenant_id: Tenant ID for isolation
            chat_id: Chat ID to retrieve

        Returns:
            Optional[Chat]: Chat instance or None if not found
        """
        query = select(Chat).where(
            Chat.id == chat_id,
            Chat.tenant_id == tenant_id,
            Chat.is_active.is_(True),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_chats(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        restrict_to_user: Optional[UUID] = None,
    ) -> tuple[list[Chat], int]:
        """
        List all chats for a tenant (paginated).

        Args:
            tenant_id: Tenant ID for isolation
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            tuple[list[Chat], int]: (chats, total_count)
        """
        base_filters = [
            Chat.tenant_id == tenant_id,
            Chat.is_active.is_(True),
        ]

        count_query = select(func.count(Chat.id)).where(*base_filters)
        query = (
            select(Chat)
            .where(*base_filters)
            .order_by(Chat.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if restrict_to_user:
            count_query = count_query.join(
                ChatAccess, ChatAccess.chat_id == Chat.id
            ).where(
                ChatAccess.user_id == restrict_to_user,
                ChatAccess.tenant_id == tenant_id,
            )
            query = query.join(ChatAccess, ChatAccess.chat_id == Chat.id).where(
                ChatAccess.user_id == restrict_to_user,
                ChatAccess.tenant_id == tenant_id,
            )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        result = await self.db.execute(query)
        chats = result.scalars().all()

        return list(chats), total

    async def update_chat(
        self, tenant_id: UUID, chat_id: UUID, data: ChatUpdateRequest
    ) -> Optional[Chat]:
        """
        Update chat configuration with tenant isolation.

        Args:
            tenant_id: Tenant ID for isolation
            chat_id: Chat ID to update
            data: Update data

        Returns:
            Optional[Chat]: Updated chat or None if not found
        """
        # Get existing chat
        chat = await self.get_chat(tenant_id, chat_id)
        if not chat:
            return None

        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)

        # If name is updated, regenerate slug
        if "name" in update_data:
            new_slug = generate_slug(update_data["name"])
            # Ensure slug is unique (exclude current chat)
            new_slug = await self._ensure_unique_slug(
                tenant_id, new_slug, exclude_chat_id=chat_id
            )
            update_data["slug"] = new_slug

        # Apply updates
        for field, value in update_data.items():
            setattr(chat, field, value)

        await self.db.commit()
        await self.db.refresh(chat)

        return chat

    async def delete_chat(self, tenant_id: UUID, chat_id: UUID) -> bool:
        """
        Soft delete a chat (set is_active = False).

        Args:
            tenant_id: Tenant ID for isolation
            chat_id: Chat ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        chat = await self.get_chat(tenant_id, chat_id)
        if not chat:
            return False

        chat.is_active = False
        await self.db.commit()

        return True

    def _auto_configure_rag_settings(
        self, purpose: str, sensitivity: str, document_languages: list[str]
    ) -> dict:
        """
        Smart defaults based on chat configuration.

        Examples:
        - If sensitivity="high_on_prem" → use local embedding model
        - If languages include "uz" → use multilingual-e5-large
        - If purpose="hr_assistant" → retrieval_strategy="hybrid"
        - If purpose="policy_qa" → retrieval_strategy="graph_priority"

        Args:
            purpose: Chat purpose
            sensitivity: Data sensitivity level
            document_languages: List of document languages

        Returns:
            dict: RAG configuration with embedding_model, llm_model,
                  retrieval_strategy, max_context_chunks
        """
        config = {
            "embedding_model": "intfloat/multilingual-e5-large",
            "llm_model": "qwen2.5:14b",
            "retrieval_strategy": "hybrid",
            "max_context_chunks": 10,
        }

        # Adjust embedding model based on sensitivity and languages
        if sensitivity == "high_on_prem":
            # Use local model for high sensitivity
            config["embedding_model"] = "intfloat/multilingual-e5-large"
        elif "uz" in document_languages or "ru" in document_languages:
            # Multilingual model for Uzbek/Russian
            config["embedding_model"] = "intfloat/multilingual-e5-large"
        else:
            # English-only can use smaller model
            config["embedding_model"] = "sentence-transformers/all-MiniLM-L6-v2"

        # Adjust LLM based on sensitivity
        if sensitivity == "high_on_prem":
            config["llm_model"] = "qwen2.5:14b"  # Local model
        else:
            config["llm_model"] = "qwen2.5:14b"

        # Adjust retrieval strategy based on purpose
        if purpose == "policy_qa":
            # Policy QA benefits from graph-based retrieval
            config["retrieval_strategy"] = "graph_priority"
            config["max_context_chunks"] = 8
        elif purpose == "hr_assistant":
            # HR assistant uses hybrid retrieval
            config["retrieval_strategy"] = "hybrid"
            config["max_context_chunks"] = 10
        elif purpose == "sop_helper":
            # SOP helper needs more context for procedures
            config["retrieval_strategy"] = "hybrid"
            config["max_context_chunks"] = 15
        elif purpose == "product_docs":
            # Product docs use dense retrieval
            config["retrieval_strategy"] = "dense_only"
            config["max_context_chunks"] = 12
        else:
            # Default hybrid approach
            config["retrieval_strategy"] = "hybrid"
            config["max_context_chunks"] = 10

        return config

    async def _ensure_unique_slug(
        self, tenant_id: UUID, slug: str, exclude_chat_id: Optional[UUID] = None
    ) -> str:
        """
        Ensure slug is unique within tenant by appending number if needed.

        Args:
            tenant_id: Tenant ID
            slug: Proposed slug
            exclude_chat_id: Chat ID to exclude from uniqueness check (for updates)

        Returns:
            str: Unique slug
        """
        original_slug = slug
        counter = 1

        while True:
            # Check if slug exists
            query = select(Chat).where(
                Chat.tenant_id == tenant_id,
                Chat.slug == slug,
                Chat.is_active.is_(True),
            )
            if exclude_chat_id:
                query = query.where(Chat.id != exclude_chat_id)

            result = await self.db.execute(query)
            existing = result.scalar_one_or_none()

            if not existing:
                return slug

            # Slug exists, try with counter
            slug = f"{original_slug}-{counter}"
            counter += 1
