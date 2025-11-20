"""Graph service for building and querying document graphs."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import GraphBuildError, GraphNotFoundError
from app.models.atomic_unit import AtomicUnit
from app.models.document_graph import DocumentGraph
from app.services.graph.graph_builder import GraphBuilder
from app.services.graph.node import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service for building and querying document graphs.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize graph service.

        Args:
            db: Database session
        """
        self.db = db
        self.graph_builder = GraphBuilder()
        self.logger = logger

    async def build_graph(self, chat_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """
        Build document graph for a chat.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID

        Returns:
            Dict with graph statistics

        Raises:
            GraphBuildError: If graph building fails
        """
        try:
            self.logger.info(f"Building graph for chat {chat_id}")

            # 1. Load atomic units
            atomic_units = await self._load_atomic_units(chat_id, tenant_id)
            if not atomic_units:
                raise GraphBuildError(f"No atomic units found for chat {chat_id}")

            # 2. Build graph structure
            nodes, edges = self.graph_builder.build_graph(atomic_units)

            # 3. Convert to JSON-serializable format
            nodes_dict = {node_id: node.to_dict() for node_id, node in nodes.items()}
            edges_list = [edge.to_dict() for edge in edges]

            # 4. Calculate metadata
            graph_metadata = self._calculate_metadata(nodes, edges)

            # 5. Save to database
            await self._save_graph(
                chat_id=chat_id,
                tenant_id=tenant_id,
                nodes=nodes_dict,
                edges=edges_list,
                metadata=graph_metadata,
            )

            self.logger.info(
                f"Graph built for chat {chat_id}: "
                f"{len(nodes)} nodes, {len(edges)} edges"
            )

            return {
                "chat_id": str(chat_id),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "metadata": graph_metadata,
                "status": "success",
            }

        except Exception as e:
            self.logger.error(f"Graph building failed: {e}")
            raise GraphBuildError(f"Failed to build graph: {e}")

    async def get_neighbors(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        node_id: str,
        edge_type: Optional[str] = None,
        hops: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get neighboring nodes in the graph.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID
            node_id: Starting node ID
            edge_type: Filter by edge type (CONTAINS, NEXT, REFERS_TO)
            hops: Number of hops (default: 1)

        Returns:
            List of neighbor nodes with their data

        Raises:
            GraphNotFoundError: If graph doesn't exist
        """
        graph = await self._load_graph(chat_id, tenant_id)
        if not graph:
            raise GraphNotFoundError(f"Graph not found for chat {chat_id}")

        # Find all edges from this node
        neighbors = []
        visited = {node_id}
        current_layer = [node_id]

        for hop in range(hops):
            next_layer = []

            for current_id in current_layer:
                for edge in graph["edges"]:
                    # Check if edge starts from current node
                    if edge["source_id"] == current_id:
                        # Filter by edge type if specified
                        if edge_type is None or edge["edge_type"] == edge_type:
                            target_id = edge["target_id"]
                            if target_id not in visited:
                                visited.add(target_id)
                                next_layer.append(target_id)

                                # Add node data
                                if target_id in graph["nodes"]:
                                    neighbors.append(
                                        {
                                            "node": graph["nodes"][target_id],
                                            "edge": edge,
                                            "distance": hop + 1,
                                        }
                                    )

            current_layer = next_layer

        return neighbors

    async def _load_atomic_units(
        self, chat_id: UUID, tenant_id: UUID
    ) -> List[AtomicUnit]:
        """
        Load all atomic units for a chat.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID

        Returns:
            List of atomic units
        """
        query = (
            select(AtomicUnit)
            .where(AtomicUnit.chat_id == chat_id, AtomicUnit.tenant_id == tenant_id)
            .order_by(AtomicUnit.sequence)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _calculate_metadata(
        self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]
    ) -> Dict[str, Any]:
        """
        Calculate graph metadata/statistics.

        Args:
            nodes: Dictionary of graph nodes
            edges: List of graph edges

        Returns:
            Metadata dictionary
        """
        edge_type_counts = {}
        node_type_counts = {}

        for edge in edges:
            edge_type = edge.edge_type
            edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1

        for node in nodes.values():
            node_type = node.node_type
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

        return {
            "edge_type_counts": edge_type_counts,
            "node_type_counts": node_type_counts,
            "avg_node_degree": len(edges) / len(nodes) if nodes else 0,
        }

    async def _save_graph(
        self,
        chat_id: UUID,
        tenant_id: UUID,
        nodes: Dict[str, Any],
        edges: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> None:
        """
        Save graph to database.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID
            nodes: Nodes dictionary
            edges: Edges list
            metadata: Graph metadata
        """
        query = select(DocumentGraph).where(DocumentGraph.chat_id == chat_id)
        result = await self.db.execute(query)
        existing_graph = result.scalar_one_or_none()

        if existing_graph:
            # Update existing graph
            existing_graph.nodes = nodes
            existing_graph.edges = edges
            existing_graph.node_count = len(nodes)
            existing_graph.edge_count = len(edges)
            existing_graph.graph_metadata = metadata
            existing_graph.updated_at = datetime.utcnow()
        else:
            # Create new graph
            new_graph = DocumentGraph(
                tenant_id=tenant_id,
                chat_id=chat_id,
                nodes=nodes,
                edges=edges,
                node_count=len(nodes),
                edge_count=len(edges),
                graph_metadata=metadata,
            )
            self.db.add(new_graph)

        await self.db.commit()

    async def _load_graph(
        self, chat_id: UUID, tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Load graph from database.

        Args:
            chat_id: Chat UUID
            tenant_id: Tenant UUID

        Returns:
            Graph data or None if not found
        """
        query = select(DocumentGraph).where(
            DocumentGraph.chat_id == chat_id, DocumentGraph.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        graph = result.scalar_one_or_none()

        if not graph:
            return None

        return {
            "nodes": graph.nodes,
            "edges": graph.edges,
            "metadata": graph.graph_metadata,
        }
