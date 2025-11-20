"""Dense vector retriever using embeddings and Qdrant."""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.embedding_service import EmbeddingService
from app.services.retrieval.base_retriever import BaseRetriever
from app.services.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)


class DenseRetriever(BaseRetriever):
    """Dense vector retriever using embeddings and Qdrant."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
    ):
        """
        Initialize dense retriever.

        Args:
            db: Database session
            embedding_service: Service for generating embeddings
            vector_store: Qdrant vector store instance
        """
        self.db = db
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.logger = logger

    async def retrieve(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using dense vector similarity.

        Args:
            chat_id: Chat identifier
            tenant_id: Tenant identifier
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of retrieved results with scores and metadata
        """
        try:
            # 1. Embed query
            query_vector = self.embedding_service.embed_query(query)

            # 2. Search Qdrant
            results = self.vector_store.search(
                chat_id=chat_id,
                query_vector=query_vector,
                tenant_id=tenant_id,
                limit=top_k,
                score_threshold=score_threshold,
            )

            # 3. Format results
            formatted = []
            for result in results:
                formatted.append(
                    {
                        "atomic_unit_id": result["id"],
                        "score": result["score"],
                        "source": "dense",
                        "metadata": result["payload"],
                    }
                )

            self.logger.info(f"Dense retrieval: {len(formatted)} results")
            return formatted

        except Exception as e:
            self.logger.error(f"Dense retrieval failed: {e}")
            return []
