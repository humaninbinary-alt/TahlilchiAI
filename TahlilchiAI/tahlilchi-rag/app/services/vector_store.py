"""Qdrant vector store service for managing vector operations."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings
from app.core.exceptions import CollectionNotFoundError, VectorStoreError

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """
    Service for managing Qdrant vector store operations.

    - Each chat gets its own collection for isolation
    - Collection naming: chat_{chat_id}
    - Supports multi-tenant filtering via payload
    """

    def __init__(
        self, url: str = settings.QDRANT_URL, api_key: str = settings.QDRANT_API_KEY
    ):
        """
        Initialize Qdrant client.

        Args:
            url: Qdrant server URL
            api_key: API key (empty for local)
        """
        self.url = url
        self.api_key = api_key if api_key else None
        self._client: Optional[QdrantClient] = None
        self.logger = logger

    @property
    def client(self) -> QdrantClient:
        """
        Lazy initialize Qdrant client.

        Returns:
            Connected QdrantClient instance

        Raises:
            VectorStoreError: If connection fails
        """
        if self._client is None:
            try:
                self.logger.info(f"Connecting to Qdrant at {self.url}")
                self._client = QdrantClient(
                    url=self.url, api_key=self.api_key, timeout=30
                )
                # Test connection
                self._client.get_collections()
                self.logger.info("Successfully connected to Qdrant")
            except Exception as e:
                self.logger.error(f"Failed to connect to Qdrant: {e}")
                raise VectorStoreError(f"Cannot connect to Qdrant: {e}")
        return self._client

    def create_collection(
        self, chat_id: UUID, dimension: int = settings.EMBEDDING_DIMENSION
    ) -> str:
        """
        Create a new Qdrant collection for a chat.

        Args:
            chat_id: Chat UUID
            dimension: Vector dimension (default: 1024)

        Returns:
            Collection name

        Raises:
            VectorStoreError: If collection creation fails
        """
        collection_name = self._get_collection_name(chat_id)

        try:
            # Check if collection already exists
            existing = self.client.get_collections().collections
            if any(c.name == collection_name for c in existing):
                self.logger.info(f"Collection {collection_name} already exists")
                return collection_name

            # Create collection with cosine similarity
            self.logger.info(f"Creating collection: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            self.logger.info(f"Collection created: {collection_name}")
            return collection_name

        except Exception as e:
            self.logger.error(f"Collection creation failed: {e}")
            raise VectorStoreError(f"Failed to create collection: {e}")

    def index_points(self, chat_id: UUID, points: List[Dict[str, Any]]) -> int:
        """
        Index multiple points (atomic units) into Qdrant.

        Args:
            chat_id: Chat UUID
            points: List of dicts with structure:
                {
                    'id': str (atomic_unit_id),
                    'vector': List[float],
                    'payload': {
                        'tenant_id': str,
                        'document_id': str,
                        'text': str,
                        'unit_type': str,
                        'sequence': int,
                        'page_number': int | None,
                        'section_title': str | None,
                        ...
                    }
                }

        Returns:
            Number of points indexed

        Raises:
            VectorStoreError: If indexing fails
        """
        collection_name = self._get_collection_name(chat_id)

        try:
            # Convert to PointStruct objects
            qdrant_points = [
                PointStruct(
                    id=point["id"], vector=point["vector"], payload=point["payload"]
                )
                for point in points
            ]

            self.logger.info(
                f"Indexing {len(qdrant_points)} points to {collection_name}"
            )

            # Upsert points (insert or update)
            self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points,
                wait=True,  # Wait for indexing to complete
            )

            self.logger.info(f"Successfully indexed {len(qdrant_points)} points")
            return len(qdrant_points)

        except Exception as e:
            self.logger.error(f"Point indexing failed: {e}")
            raise VectorStoreError(f"Failed to index points: {e}")

    def search(
        self,
        chat_id: UUID,
        query_vector: List[float],
        tenant_id: UUID,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in a collection.

        Args:
            chat_id: Chat UUID
            query_vector: Query embedding
            tenant_id: Tenant ID for filtering
            limit: Max results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of search results with payload and score

        Raises:
            CollectionNotFoundError: If collection doesn't exist
            VectorStoreError: If search fails
        """
        collection_name = self._get_collection_name(chat_id)

        try:
            # Search with tenant filter
            # Note: Qdrant client v1.16+ uses query_points instead of search
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="tenant_id", match=MatchValue(value=str(tenant_id))
                        )
                    ]
                ),
                limit=limit,
                score_threshold=score_threshold,
            )

            # Convert to dict format
            return [
                {"id": point.id, "score": point.score, "payload": point.payload}
                for point in results.points
            ]

        except Exception as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(f"Collection {collection_name} not found")
            self.logger.error(f"Search failed: {e}")
            raise VectorStoreError(f"Search failed: {e}")

    def delete_collection(self, chat_id: UUID) -> bool:
        """
        Delete a collection (when chat is deleted).

        Args:
            chat_id: Chat UUID

        Returns:
            True if deleted successfully
        """
        collection_name = self._get_collection_name(chat_id)
        try:
            self.client.delete_collection(collection_name)
            self.logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Collection deletion failed: {e}")
            return False

    def _get_collection_name(self, chat_id: UUID) -> str:
        """
        Generate collection name from chat_id.

        Args:
            chat_id: Chat UUID

        Returns:
            Collection name string
        """
        return f"{settings.QDRANT_COLLECTION_PREFIX}_{str(chat_id)}"
