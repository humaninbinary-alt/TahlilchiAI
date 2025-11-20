"""Main retrieval engine combining multiple strategies."""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidRetrievalModeError, RetrievalError
from app.models.atomic_unit import AtomicUnit
from app.schemas.retrieval import RetrievalMode, RetrievalRequest, RetrievedContext
from app.services.graph.graph_service import GraphService
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.fusion import ReciprocalRankFusion
from app.services.retrieval.sparse_retriever import SparseRetriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Main retrieval engine combining multiple strategies.

    Modes:
    - dense_only: Vector search
    - sparse_only: BM25 search
    - hybrid: Dense + Sparse with RRF fusion
    - graph_enhanced: Hybrid + graph neighbor expansion
    """

    def __init__(
        self,
        db: AsyncSession,
        dense_retriever: DenseRetriever,
        sparse_retriever: SparseRetriever,
        graph_service: GraphService,
    ):
        """
        Initialize hybrid retriever.

        Args:
            db: Database session
            dense_retriever: Dense vector retriever
            sparse_retriever: Sparse BM25 retriever
            graph_service: Graph service for neighbor expansion
        """
        self.db = db
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.graph_service = graph_service
        self.fusion = ReciprocalRankFusion()
        self.logger = logger

    async def retrieve(
        self, chat_id: UUID, tenant_id: UUID, request: RetrievalRequest
    ) -> List[RetrievedContext]:
        """
        Main retrieval method with mode selection.

        Args:
            chat_id: Chat identifier
            tenant_id: Tenant identifier
            request: Retrieval request with parameters

        Returns:
            List of retrieved contexts

        Raises:
            RetrievalError: If retrieval fails
            InvalidRetrievalModeError: If mode is invalid
        """
        try:
            self.logger.info(
                f"Retrieving for query: '{request.query}' "
                f"mode: {request.mode}, top_k: {request.top_k}"
            )

            # 1. Retrieve based on mode
            if request.mode == RetrievalMode.DENSE_ONLY:
                results = await self._dense_only(
                    chat_id,
                    tenant_id,
                    request.query,
                    request.top_k,
                    request.score_threshold,
                )

            elif request.mode == RetrievalMode.SPARSE_ONLY:
                results = await self._sparse_only(
                    chat_id, tenant_id, request.query, request.top_k
                )

            elif request.mode == RetrievalMode.HYBRID:
                results = await self._hybrid(
                    chat_id,
                    tenant_id,
                    request.query,
                    request.top_k,
                    request.score_threshold,
                )

            elif request.mode == RetrievalMode.GRAPH_ENHANCED:
                results = await self._graph_enhanced(
                    chat_id, tenant_id, request, request.score_threshold
                )

            else:
                raise InvalidRetrievalModeError(f"Invalid mode: {request.mode}")

            # 2. Expand with graph neighbors if requested
            if (
                request.expand_with_neighbors
                and request.mode != RetrievalMode.GRAPH_ENHANCED
            ):
                results = await self._expand_with_neighbors(
                    chat_id, tenant_id, results, request.neighbor_hops
                )

            # 3. Load full atomic unit data
            contexts = await self._enrich_results(results)

            # 4. Apply score threshold and limit
            contexts = [c for c in contexts if c.score >= request.score_threshold]
            contexts = contexts[: request.top_k]

            self.logger.info(f"Retrieved {len(contexts)} contexts")
            return contexts

        except Exception as e:
            self.logger.error(f"Retrieval failed: {e}")
            # Rollback the transaction to clear any failed state
            await self.db.rollback()
            raise RetrievalError(f"Retrieval failed: {e}")

    async def _dense_only(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        query: str,
        top_k: int,
        score_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Dense vector search only."""
        return await self.dense_retriever.retrieve(
            chat_id, tenant_id, query, top_k, score_threshold
        )

    async def _sparse_only(
        self, chat_id: UUID, tenant_id: UUID, query: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """BM25 sparse search only."""
        return await self.sparse_retriever.retrieve(chat_id, tenant_id, query, top_k)

    async def _hybrid(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        query: str,
        top_k: int,
        score_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Hybrid: Dense + Sparse with RRF fusion."""
        # Get results from both retrievers
        dense_results = await self.dense_retriever.retrieve(
            chat_id, tenant_id, query, top_k * 2, score_threshold  # Get more for fusion
        )

        sparse_results = await self.sparse_retriever.retrieve(
            chat_id, tenant_id, query, top_k * 2
        )

        # Fuse with RRF (slightly favor dense)
        fused = self.fusion.fuse(
            [dense_results, sparse_results], weights=[0.6, 0.4]  # 60% dense, 40% sparse
        )

        return fused[:top_k]

    async def _graph_enhanced(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        request: RetrievalRequest,
        score_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Graph-enhanced: Hybrid + automatic neighbor expansion."""
        # Start with hybrid retrieval
        hybrid_results = await self._hybrid(
            chat_id, tenant_id, request.query, request.top_k, score_threshold
        )

        # Expand with neighbors
        expanded = await self._expand_with_neighbors(
            chat_id, tenant_id, hybrid_results, request.neighbor_hops
        )

        return expanded

    async def _expand_with_neighbors(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        results: List[Dict[str, Any]],
        hops: int,
    ) -> List[Dict[str, Any]]:
        """
        Expand results with graph neighbors.

        For each result, find neighboring nodes (CONTAINS, NEXT edges)
        and add them with reduced score.
        """
        expanded = []
        seen_ids = set()

        for result in results:
            node_id = result["atomic_unit_id"]

            # Add original result
            if node_id not in seen_ids:
                expanded.append(result)
                seen_ids.add(node_id)

            # Get neighbors
            try:
                neighbors = await self.graph_service.get_neighbors(
                    chat_id=chat_id,
                    tenant_id=tenant_id,
                    node_id=node_id,
                    edge_type=None,  # All edge types
                    hops=hops,
                )

                # Add neighbors with decayed score
                for neighbor in neighbors:
                    neighbor_id = neighbor["node"]["node_id"]
                    if neighbor_id not in seen_ids:
                        # Decay score based on distance
                        distance_penalty = 0.8 ** neighbor["distance"]
                        neighbor_score = result["score"] * distance_penalty

                        expanded.append(
                            {
                                "atomic_unit_id": neighbor_id,
                                "score": neighbor_score,
                                "source": "graph",
                                "metadata": neighbor["node"],
                                "graph_distance": neighbor["distance"],
                            }
                        )
                        seen_ids.add(neighbor_id)

            except Exception as e:
                self.logger.warning(f"Failed to get neighbors for {node_id}: {e}")
                continue

        # Re-sort by score
        expanded.sort(key=lambda x: x["score"], reverse=True)

        self.logger.info(f"Expanded from {len(results)} to {len(expanded)} results")
        return expanded

    async def _enrich_results(
        self, results: List[Dict[str, Any]]
    ) -> List[RetrievedContext]:
        """Load full atomic unit data for results."""
        if not results:
            return []

        try:
            # Get atomic unit IDs
            unit_ids = [r["atomic_unit_id"] for r in results]
            self.logger.info(f"Loading {len(unit_ids)} atomic units from database")

            # Load from database with error handling
            query = select(AtomicUnit).where(AtomicUnit.id.in_(unit_ids))
            db_results = await self.db.execute(query)
            units = {str(u.id): u for u in db_results.scalars().all()}

            self.logger.info(
                f"Found {len(units)} units in database (requested {len(unit_ids)})"
            )

            # Build context objects
            contexts = []
            for result in results:
                unit_id = result["atomic_unit_id"]
                unit = units.get(unit_id)

                if unit:
                    contexts.append(
                        RetrievedContext(
                            atomic_unit_id=unit_id,
                            text=unit.text,
                            score=result["score"],
                            source=result.get("source", "unknown"),
                            document_id=str(unit.document_id),
                            unit_type=unit.unit_type,
                            sequence=unit.sequence,
                            page_number=unit.page_number,
                            section_title=unit.section_title,
                            dense_score=result.get("dense_score"),
                            sparse_score=result.get("sparse_score"),
                            graph_distance=result.get("graph_distance"),
                        )
                    )
                else:
                    self.logger.warning(f"Atomic unit {unit_id} not found in database")

            return contexts

        except Exception as e:
            self.logger.error(f"Failed to enrich results: {e}")
            # Return empty list instead of failing completely
            return []
