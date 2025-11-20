"""API endpoints for document graph operations."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_chat, get_db
from app.core.auth import get_current_user
from app.core.exceptions import GraphError, GraphNotFoundError
from app.models.chat import Chat
from app.models.user import User
from app.services.graph.graph_service import GraphService

router = APIRouter(prefix="/chats/{chat_id}/graph", tags=["graph"])


class GraphBuildResponse(BaseModel):
    """Response schema for graph build operation."""

    chat_id: str
    node_count: int
    edge_count: int
    metadata: Dict[str, Any]
    status: str


class NeighborsResponse(BaseModel):
    """Response schema for neighbors query."""

    neighbors: List[Dict[str, Any]]
    total: int


@router.post("/build", status_code=202, response_model=GraphBuildResponse)
async def build_graph(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    chat: Chat = Depends(get_current_chat),
    db: AsyncSession = Depends(get_db),
):
    """
    Build document structure graph for a chat.

    Creates:
    - Nodes from atomic units
    - Hierarchy edges (CONTAINS)
    - Sequence edges (NEXT)
    - Reference edges (REFERS_TO)

    Args:
        chat_id: Chat UUID
        tenant_id: Tenant UUID (currently from query param, will be from auth)
        db: Database session

    Returns:
        Graph build statistics

    Raises:
        HTTPException: If graph building fails
    """
    graph_service = GraphService(db)

    try:
        result = await graph_service.build_graph(
            chat_id=chat.id, tenant_id=current_user.tenant_id
        )
        return GraphBuildResponse(**result)
    except GraphError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neighbors/{node_id}", response_model=NeighborsResponse)
async def get_neighbors(
    chat_id: UUID,
    node_id: str,
    edge_type: Optional[str] = Query(None, description="Filter by edge type"),
    hops: int = Query(1, ge=1, le=3, description="Number of hops (1-3)"),
    current_user: User = Depends(get_current_user),
    chat: Chat = Depends(get_current_chat),
    db: AsyncSession = Depends(get_db),
):
    """
    Get neighboring nodes in the graph.

    Useful for:
    - Finding all subsections under a section
    - Getting next/previous paragraphs
    - Finding what references a clause

    Args:
        chat_id: Chat UUID
        node_id: Starting node ID
        tenant_id: Tenant UUID (currently from query param, will be from auth)
        edge_type: Optional edge type filter
        hops: Number of hops to traverse
        db: Database session

    Returns:
        List of neighboring nodes

    Raises:
        HTTPException: If graph not found or query fails
    """
    graph_service = GraphService(db)

    try:
        neighbors = await graph_service.get_neighbors(
            chat_id=chat.id,
            tenant_id=current_user.tenant_id,
            node_id=node_id,
            edge_type=edge_type,
            hops=hops,
        )
        return NeighborsResponse(neighbors=neighbors, total=len(neighbors))
    except GraphNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GraphError as e:
        raise HTTPException(status_code=500, detail=str(e))
