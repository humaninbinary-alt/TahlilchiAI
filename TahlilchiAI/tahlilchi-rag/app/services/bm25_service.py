"""BM25 sparse indexing service for keyword-based search."""

import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BM25BuildError, BM25Error, BM25IndexNotFoundError
from app.models.atomic_unit import AtomicUnit
from app.models.bm25_index import BM25Index
from app.services.tokenizer import MultilingualTokenizer

logger = logging.getLogger(__name__)


class BM25Service:
    """
    Service for building and searching BM25 sparse indexes.

    BM25 (Best Matching 25) is a probabilistic ranking function
    for keyword-based search. Excellent for:
    - Exact phrase matching
    - Technical terms, IDs, article numbers
    - Complementing dense vector search
    """

    def __init__(self, db: AsyncSession, tokenizer: MultilingualTokenizer):
        """
        Initialize BM25 service.

        Args:
            db: Database session
            tokenizer: Tokenizer for text processing
        """
        self.db = db
        self.tokenizer = tokenizer
        self.logger = logger

    async def build_index(self, chat_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """
        Build BM25 index for a chat from all its atomic units.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID for isolation

        Returns:
            Dict with build statistics

        Raises:
            BM25BuildError: If index building fails
        """
        try:
            self.logger.info(f"Building BM25 index for chat {chat_id}")

            # 1. Load all atomic units for this chat
            atomic_units = await self._load_atomic_units(chat_id, tenant_id)
            if not atomic_units:
                raise BM25BuildError(f"No atomic units found for chat {chat_id}")

            # 2. Tokenize all documents
            corpus_tokens = []
            doc_ids = []
            doc_metadata = []

            for unit in atomic_units:
                tokens = self.tokenizer.tokenize(unit.text)
                corpus_tokens.append(tokens)
                doc_ids.append(str(unit.id))
                doc_metadata.append(
                    {
                        "document_id": str(unit.document_id),
                        "unit_type": unit.unit_type,
                        "sequence": unit.sequence,
                        "page_number": unit.page_number,
                        "section_title": unit.section_title,
                    }
                )

            # 3. Calculate statistics
            total_tokens = sum(len(tokens) for tokens in corpus_tokens)

            # 4. Save to database
            await self._save_index(
                chat_id=chat_id,
                tenant_id=tenant_id,
                corpus_tokens=corpus_tokens,
                doc_ids=doc_ids,
                doc_metadata=doc_metadata,
                document_count=len(atomic_units),
                total_tokens=total_tokens,
            )

            self.logger.info(
                f"BM25 index built for chat {chat_id}: "
                f"{len(atomic_units)} documents, {total_tokens} tokens"
            )

            return {
                "chat_id": str(chat_id),
                "document_count": len(atomic_units),
                "total_tokens": total_tokens,
                "status": "success",
            }

        except Exception as e:
            self.logger.error(f"BM25 index building failed: {e}")
            raise BM25BuildError(f"Failed to build BM25 index: {e}")

    async def search(
        self, chat_id: UUID, tenant_id: UUID, query: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search BM25 index for relevant documents.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID for isolation
            query: Search query text
            top_k: Number of results to return

        Returns:
            List of results with scores and metadata
            [
                {
                    'atomic_unit_id': str,
                    'score': float,
                    'metadata': dict
                },
                ...
            ]

        Raises:
            BM25IndexNotFoundError: If index doesn't exist
            BM25Error: If search fails
        """
        try:
            self.logger.info(f"BM25 search in chat {chat_id}: '{query}'")

            # 1. Load index from DB
            index_data = await self._load_index(chat_id, tenant_id)
            if not index_data:
                raise BM25IndexNotFoundError(f"BM25 index not found for chat {chat_id}")

            # 2. Reconstruct BM25 object
            bm25 = BM25Okapi(index_data["corpus_tokens"])

            # 3. Tokenize query
            query_tokens = self.tokenizer.tokenize(query)

            # 4. Get BM25 scores
            scores = bm25.get_scores(query_tokens)

            # 5. Get top-k results
            top_indices = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:top_k]

            # 6. Format results
            results = []
            for idx in top_indices:
                score = float(scores[idx])
                if score > 0:  # Only return results with positive scores
                    results.append(
                        {
                            "atomic_unit_id": index_data["doc_ids"][idx],
                            "score": score,
                            "metadata": index_data["doc_metadata"][idx],
                        }
                    )

            self.logger.info(f"BM25 search returned {len(results)} results")
            return results

        except BM25IndexNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"BM25 search failed: {e}")
            raise BM25Error(f"Search failed: {e}")

    async def _load_atomic_units(
        self, chat_id: UUID, tenant_id: UUID
    ) -> List[AtomicUnit]:
        """
        Load all atomic units for a chat.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID

        Returns:
            List of AtomicUnit objects
        """
        query = (
            select(AtomicUnit)
            .where(AtomicUnit.chat_id == chat_id, AtomicUnit.tenant_id == tenant_id)
            .order_by(AtomicUnit.sequence)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _save_index(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        corpus_tokens: List[List[str]],
        doc_ids: List[str],
        doc_metadata: List[Dict[str, Any]],
        document_count: int,
        total_tokens: int,
    ) -> None:
        """
        Save BM25 index to database.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID
            corpus_tokens: Tokenized documents
            doc_ids: Document IDs
            doc_metadata: Document metadata
            document_count: Number of documents
            total_tokens: Total token count
        """
        # Check if index already exists
        query = select(BM25Index).where(BM25Index.chat_id == chat_id)
        result = await self.db.execute(query)
        existing_index = result.scalar_one_or_none()

        if existing_index:
            # Update existing index
            existing_index.corpus_tokens = corpus_tokens
            existing_index.doc_ids = doc_ids
            existing_index.doc_metadata = doc_metadata
            existing_index.document_count = document_count
            existing_index.total_tokens = total_tokens
            existing_index.updated_at = datetime.utcnow()
        else:
            # Create new index
            new_index = BM25Index(
                tenant_id=tenant_id,
                chat_id=chat_id,
                corpus_tokens=corpus_tokens,
                doc_ids=doc_ids,
                doc_metadata=doc_metadata,
                document_count=document_count,
                total_tokens=total_tokens,
            )
            self.db.add(new_index)

        await self.db.commit()

    async def _load_index(
        self, chat_id: UUID, tenant_id: UUID
    ) -> Dict[str, Any] | None:
        """
        Load BM25 index from database.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID

        Returns:
            Index data dict or None if not found
        """
        query = select(BM25Index).where(
            BM25Index.chat_id == chat_id, BM25Index.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        index = result.scalar_one_or_none()

        if not index:
            return None

        return {
            "corpus_tokens": index.corpus_tokens,
            "doc_ids": index.doc_ids,
            "doc_metadata": index.doc_metadata,
            "document_count": index.document_count,
            "total_tokens": index.total_tokens,
        }

    async def delete_index(self, chat_id: UUID, tenant_id: UUID) -> bool:
        """
        Delete BM25 index for a chat.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID

        Returns:
            True if deleted successfully
        """
        query = select(BM25Index).where(
            BM25Index.chat_id == chat_id, BM25Index.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        index = result.scalar_one_or_none()

        if index:
            await self.db.delete(index)
            await self.db.commit()
            self.logger.info(f"Deleted BM25 index for chat {chat_id}")
            return True
        return False
