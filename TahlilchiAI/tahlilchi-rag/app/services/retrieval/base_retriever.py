"""Abstract base class for all retrieval strategies."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from uuid import UUID


class BaseRetriever(ABC):
    """Abstract base class for all retrievers."""

    @abstractmethod
    async def retrieve(
        self, chat_id: UUID, tenant_id: UUID, query: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.

        Args:
            chat_id: Chat identifier
            tenant_id: Tenant identifier
            query: Search query
            top_k: Number of results to return

        Returns:
            List of dicts with keys:
                - atomic_unit_id: str
                - score: float
                - metadata: dict
        """
        pass
