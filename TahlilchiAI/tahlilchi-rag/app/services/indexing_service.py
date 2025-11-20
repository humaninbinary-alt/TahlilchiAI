"""Indexing service orchestrator for the vector embedding pipeline."""

import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IndexingError
from app.models.atomic_unit import AtomicUnit
from app.models.document import Document
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)


class IndexingService:
    """
    Orchestrates the indexing pipeline:
    1. Load atomic units from DB
    2. Generate embeddings
    3. Store in Qdrant
    4. Update document status
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
    ):
        """
        Initialize indexing service.

        Args:
            db: Database session
            embedding_service: Service for generating embeddings
            vector_store: Service for vector storage operations
        """
        self.db = db
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.logger = logger

    async def index_document(
        self, document_id: UUID, tenant_id: UUID, chat_id: UUID
    ) -> Dict[str, Any]:
        """
        Index a document's atomic units into Qdrant.

        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID
            chat_id: Chat UUID

        Returns:
            Dict with indexing stats

        Raises:
            IndexingError: If indexing fails
        """
        try:
            self.logger.info(f"Starting indexing for document {document_id}")

            # 1. Ensure collection exists
            self.vector_store.create_collection(chat_id)

            # 2. Load atomic units
            atomic_units = await self._load_atomic_units(document_id, tenant_id)
            if not atomic_units:
                raise IndexingError(f"No atomic units found for document {document_id}")

            self.logger.info(f"Loaded {len(atomic_units)} atomic units")

            # 3. Generate embeddings in batch
            texts = [unit.text for unit in atomic_units]
            embeddings = self.embedding_service.embed_batch(texts)

            # 4. Prepare points for Qdrant
            points = self._prepare_points(atomic_units, embeddings, tenant_id)

            # 5. Index into Qdrant
            indexed_count = self.vector_store.index_points(chat_id, points)

            # 6. Update document status
            await self._update_document_status(document_id, "indexed")

            # 7. Build BM25 index for the chat
            try:
                from app.services.bm25_service import BM25Service
                from app.services.tokenizer import MultilingualTokenizer

                tokenizer = MultilingualTokenizer()
                bm25_service = BM25Service(self.db, tokenizer)
                await bm25_service.build_index(chat_id, tenant_id)
                self.logger.info(f"BM25 index built for chat {chat_id}")
            except Exception as e:
                self.logger.warning(f"BM25 indexing failed (non-fatal): {e}")
                # Don't fail the whole indexing if BM25 fails

            # 8. Build graph structure
            try:
                from app.services.graph.graph_service import GraphService

                graph_service = GraphService(self.db)
                await graph_service.build_graph(chat_id, tenant_id)
                self.logger.info(f"Graph built for chat {chat_id}")
            except Exception as e:
                self.logger.warning(f"Graph building failed (non-fatal): {e}")
                # Don't fail the whole indexing if graph building fails

            self.logger.info(
                f"Successfully indexed {indexed_count} points for document {document_id}"
            )

            return {
                "document_id": str(document_id),
                "atomic_units_count": len(atomic_units),
                "indexed_count": indexed_count,
                "status": "indexed",
            }

        except Exception as e:
            self.logger.error(f"Indexing failed for document {document_id}: {e}")
            await self._update_document_status(document_id, "indexing_failed", str(e))
            raise IndexingError(f"Failed to index document: {e}")

    async def _load_atomic_units(
        self, document_id: UUID, tenant_id: UUID
    ) -> List[AtomicUnit]:
        """
        Load atomic units for a document.

        Args:
            document_id: Document UUID
            tenant_id: Tenant UUID

        Returns:
            List of AtomicUnit objects
        """
        query = (
            select(AtomicUnit)
            .where(
                AtomicUnit.document_id == document_id,
                AtomicUnit.tenant_id == tenant_id,
            )
            .order_by(AtomicUnit.sequence)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _prepare_points(
        self,
        atomic_units: List[AtomicUnit],
        embeddings: List[List[float]],
        tenant_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Prepare points for Qdrant indexing.

        Each point contains:
        - id: atomic_unit.id
        - vector: embedding
        - payload: all metadata needed for retrieval

        Args:
            atomic_units: List of atomic unit objects
            embeddings: List of embedding vectors
            tenant_id: Tenant UUID

        Returns:
            List of point dictionaries
        """
        points = []

        for unit, embedding in zip(atomic_units, embeddings):
            point = {
                "id": str(unit.id),
                "vector": embedding,
                "payload": {
                    "tenant_id": str(tenant_id),
                    "document_id": str(unit.document_id),
                    "chat_id": str(unit.chat_id),
                    "text": unit.text,
                    "unit_type": unit.unit_type,
                    "sequence": unit.sequence,
                    "level": unit.level,
                    "page_number": unit.page_number,
                    "section_title": unit.section_title,
                    "metadata": unit.metadata_json or {},
                },
            }
            points.append(point)

        return points

    async def _update_document_status(
        self, document_id: UUID, status: str, error_message: str = None
    ) -> None:
        """
        Update document indexing status.

        Args:
            document_id: Document UUID
            status: New status value
            error_message: Optional error message
        """
        query = select(Document).where(Document.id == document_id)
        result = await self.db.execute(query)
        document = result.scalar_one_or_none()

        if document:
            document.status = status
            if error_message:
                document.error_message = error_message
            if status == "indexed":
                document.processed_at = datetime.utcnow()
            await self.db.commit()
