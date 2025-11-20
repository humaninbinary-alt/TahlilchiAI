"""Sparse retriever using BM25 keyword matching."""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bm25_service import BM25Service
from app.services.retrieval.base_retriever import BaseRetriever

logger = logging.getLogger(__name__)


class SparseRetriever(BaseRetriever):
    """Sparse retriever using BM25 keyword matching."""

    def __init__(self, db: AsyncSession, bm25_service: BM25Service):
        """
        Initialize sparse retriever.

        Args:
            db: Database session
            bm25_service: BM25 service for keyword search
        """
        self.db = db
        self.bm25_service = bm25_service
        self.logger = logger

    async def retrieve(
        self, chat_id: UUID, tenant_id: UUID, query: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using BM25 sparse matching.

        Args:
            chat_id: Chat identifier
            tenant_id: Tenant identifier
            query: Search query
            top_k: Number of results to return

        Returns:
            List of retrieved results with scores and metadata
        """
        try:
            # Search BM25 index
            results = await self.bm25_service.search(
                chat_id=chat_id, tenant_id=tenant_id, query=query, top_k=top_k
            )

            # Format results
            formatted = []
            for result in results:
                formatted.append(
                    {
                        "atomic_unit_id": result["atomic_unit_id"],
                        "score": result["score"],
                        "source": "sparse",
                        "metadata": result["metadata"],
                    }
                )

            self.logger.info(f"Sparse retrieval: {len(formatted)} results")
            return formatted

        except Exception as e:
            self.logger.error(f"Sparse retrieval failed: {e}")
            return []
