"""API endpoints for hybrid document retrieval."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_chat, get_db
from app.core.auth import get_current_user
from app.core.exceptions import RetrievalError
from app.models.chat import Chat
from app.models.user import User
from app.schemas.retrieval import RetrievalMode, RetrievalRequest, RetrievalResponse
from app.schemas.router import RouterRequest
from app.services.bm25_service import BM25Service
from app.services.embedding_service import EmbeddingService
from app.services.graph.graph_service import GraphService
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.sparse_retriever import SparseRetriever
from app.services.router.adaptive_router import AdaptiveRouter
from app.services.tokenizer import MultilingualTokenizer
from app.services.vector_store import QdrantVectorStore

router = APIRouter(prefix="/chats/{chat_id}/retrieve", tags=["retrieval"])


@router.post("/", response_model=RetrievalResponse)
async def retrieve_contexts(
    chat_id: UUID,
    request: RetrievalRequest,
    use_adaptive_routing: bool = Query(
        default=False, description="Let router automatically select retrieval mode"
    ),
    current_user: User = Depends(get_current_user),
    chat: Chat = Depends(get_current_chat),
    db: AsyncSession = Depends(get_db),
) -> RetrievalResponse:
    """
    Retrieve relevant contexts for a query.

    Supports multiple retrieval modes:
    - dense_only: Vector similarity search
    - sparse_only: BM25 keyword search
    - hybrid: Combined dense + sparse (recommended)
    - graph_enhanced: Hybrid + graph neighbor expansion

    Args:
        chat_id: Chat identifier
        request: Retrieval request with query and parameters
        tenant_id: Tenant identifier (from auth)
        db: Database session

    Returns:
        RetrievalResponse with retrieved contexts

    Raises:
        HTTPException: If retrieval fails
    """
    # Use adaptive routing if requested
    tenant_id = current_user.tenant_id

    if use_adaptive_routing:
        # Use router to select mode
        router_request = RouterRequest(query=request.query, chat_id=str(chat_id))
        adaptive_router = AdaptiveRouter(db)
        decision = await adaptive_router.route(router_request, tenant_id)

        # Override request with router decision
        request.mode = RetrievalMode(decision.selected_mode)
        request.top_k = decision.top_k
        request.score_threshold = decision.score_threshold
        request.expand_with_neighbors = decision.expand_with_neighbors
        request.neighbor_hops = decision.neighbor_hops

    # Initialize services
    embedding_service = EmbeddingService()
    vector_store = QdrantVectorStore()
    tokenizer = MultilingualTokenizer()
    bm25_service = BM25Service(db, tokenizer)
    graph_service = GraphService(db)

    # Initialize retrievers
    dense_retriever = DenseRetriever(db, embedding_service, vector_store)
    sparse_retriever = SparseRetriever(db, bm25_service)

    # Initialize hybrid retriever
    hybrid_retriever = HybridRetriever(
        db=db,
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
        graph_service=graph_service,
    )

    try:
        # Retrieve contexts
        contexts = await hybrid_retriever.retrieve(
            chat_id=chat.id,
            tenant_id=tenant_id,
            request=request,
        )

        return RetrievalResponse(
            query=request.query,
            mode=request.mode.value,
            contexts=contexts,
            total_results=len(contexts),
            retrieval_metadata={
                "top_k": request.top_k,
                "score_threshold": request.score_threshold,
                "expand_with_neighbors": request.expand_with_neighbors,
            },
        )

    except RetrievalError as e:
        raise HTTPException(status_code=500, detail=str(e))
