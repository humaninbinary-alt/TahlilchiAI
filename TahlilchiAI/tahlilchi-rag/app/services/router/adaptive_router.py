"""Main adaptive router service for query routing."""

import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RouterError
from app.models.chat import Chat
from app.schemas.router import RouterRequest, RoutingDecision
from app.services.router.query_analyzer import QueryAnalyzer
from app.services.router.routing_strategy import RoutingStrategy

logger = logging.getLogger(__name__)


class AdaptiveRouter:
    """
    Main adaptive router service.

    Pipeline:
    1. Analyze query characteristics
    2. Load chat configuration
    3. Select optimal retrieval strategy
    4. Return routing decision
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the adaptive router.

        Args:
            db: Database session
        """
        self.db = db
        self.analyzer = QueryAnalyzer()
        self.strategy = RoutingStrategy()
        self.logger = logger

    async def route(self, request: RouterRequest, tenant_id: UUID) -> RoutingDecision:
        """
        Route a query to optimal retrieval strategy.

        Args:
            request: RouterRequest with query and chat_id
            tenant_id: Tenant UUID for isolation

        Returns:
            RoutingDecision with selected strategy

        Raises:
            RouterError: If routing fails
        """
        try:
            self.logger.info(f"Routing query: '{request.query}'")

            # 1. Analyze query
            query_chars = self.analyzer.analyze(request.query)
            self.logger.info(
                f"Query analysis: type={query_chars.query_type}, "
                f"lang={query_chars.language}, "
                f"confidence={query_chars.confidence}"
            )

            # 2. Load chat configuration
            chat_config = await self._load_chat_config(
                chat_id=UUID(request.chat_id), tenant_id=tenant_id
            )

            # 3. Make routing decision
            decision = self.strategy.decide(query_chars, chat_config)

            # 4. Apply manual overrides if provided
            if request.force_mode:
                decision.selected_mode = request.force_mode
                decision.reasoning += " (Manually overridden)"

            if request.force_top_k:
                decision.top_k = request.force_top_k

            self.logger.info(
                f"Routing decision: mode={decision.selected_mode}, "
                f"top_k={decision.top_k}, "
                f"reasoning={decision.reasoning}"
            )

            return decision

        except Exception as e:
            self.logger.error(f"Routing failed: {e}")
            raise RouterError(f"Failed to route query: {e}")

    async def _load_chat_config(self, chat_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """Load chat configuration from database."""
        try:
            query = select(Chat).where(Chat.id == chat_id, Chat.tenant_id == tenant_id)
            result = await self.db.execute(query)
            chat = result.scalar_one_or_none()
        except Exception as e:
            # If transaction failed, rollback and retry
            if "InFailedSqlTransaction" in str(
                e
            ) or "current transaction is aborted" in str(e):
                self.logger.warning("Transaction failed, rolling back and retrying...")
                await self.db.rollback()
                # Retry after rollback
                query = select(Chat).where(
                    Chat.id == chat_id, Chat.tenant_id == tenant_id
                )
                result = await self.db.execute(query)
                chat = result.scalar_one_or_none()
            else:
                raise

        if not chat:
            raise ValueError(f"Chat {chat_id} not found")

        return {
            "strictness": chat.strictness,
            "purpose": chat.purpose,
            "tone": chat.tone,
            "document_types": chat.document_types,
            "document_languages": chat.document_languages,
        }
