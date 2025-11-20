"""API endpoints for answer generation - the complete RAG pipeline."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TransactionalSession, get_chat_with_access, get_db
from app.config import settings
from app.core.auth import get_current_user
from app.core.decorators import rate_limit
from app.core.exceptions import LLMError, NoRelevantContextError
from app.models.user import User
from app.schemas.answer import AnswerRequest, AnswerResponse
from app.schemas.retrieval import RetrievalMode, RetrievalRequest
from app.schemas.router import RouterRequest
from app.services.bm25_service import BM25Service
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.services.graph.graph_service import GraphService
from app.services.llm.answer_generator import AnswerGenerator
from app.services.llm.ollama_client import OllamaClient
from app.services.llm.prompt_builder import PromptBuilder
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.sparse_retriever import SparseRetriever
from app.services.router.adaptive_router import AdaptiveRouter
from app.services.tokenizer import MultilingualTokenizer
from app.services.vector_store import QdrantVectorStore

router = APIRouter(prefix="/chats/{chat_id}/answer", tags=["answer"])


@router.post("", response_model=AnswerResponse)
@rate_limit(limit=settings.RATE_LIMIT_FREE_QUERIES, scope="user")
async def generate_answer(
    chat_id: UUID,
    payload: AnswerRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnswerResponse:
    """
    Complete RAG pipeline: Query → Retrieve → Generate Answer.

    This is the main endpoint that:
    1. Routes query to optimal retrieval strategy
    2. Retrieves relevant contexts
    3. Generates grounded answer with citations

    This is what your users will call!

    Args:
        chat_id: Chat identifier
        request: Answer request with query
        current_user: Authenticated user (enforces tenant isolation)
        db: Database session

    Returns:
        AnswerResponse with generated answer and citations

    Raises:
        HTTPException: If answer generation fails
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    tenant_id = current_user.tenant_id
    request.state.endpoint = "answer.generate"

    # Use transactional context for the entire operation
    async with TransactionalSession(db) as session:
        try:
            # Step 1: Adaptive routing
            adaptive_router = AdaptiveRouter(session)
            routing_decision = await adaptive_router.route(
                RouterRequest(query=payload.query, chat_id=str(chat_id)), tenant_id
            )

            # Step 2: Retrieve contexts
            embedding_service = EmbeddingService()
            vector_store = QdrantVectorStore()
            tokenizer = MultilingualTokenizer()
            bm25_service = BM25Service(session, tokenizer)
            graph_service = GraphService(session)

            dense_retriever = DenseRetriever(session, embedding_service, vector_store)
            sparse_retriever = SparseRetriever(session, bm25_service)
            hybrid_retriever = HybridRetriever(
                db=session,
                dense_retriever=dense_retriever,
                sparse_retriever=sparse_retriever,
                graph_service=graph_service,
            )

            retrieval_request = RetrievalRequest(
                query=payload.query,
                mode=RetrievalMode(routing_decision.selected_mode),
                top_k=routing_decision.top_k,
                score_threshold=routing_decision.score_threshold,
                expand_with_neighbors=routing_decision.expand_with_neighbors,
                neighbor_hops=routing_decision.neighbor_hops,
            )

            contexts = await hybrid_retriever.retrieve(
                chat_id=chat_id, tenant_id=tenant_id, request=retrieval_request
            )

            # Step 3: Generate answer
            llm_client = OllamaClient()
            prompt_builder = PromptBuilder()
            answer_generator = AnswerGenerator(session, llm_client, prompt_builder)

            result = await answer_generator.generate_answer(
                query=payload.query,
                contexts=contexts,
                chat_id=chat_id,
                tenant_id=tenant_id,
            )

            return AnswerResponse(
                query=payload.query,
                answer=result["answer"],
                citations=result["citations"],
                contexts_used=result["contexts_used"],
                confidence=result["confidence"],
                retrieval_mode=routing_decision.selected_mode,
                chat_config=result["chat_config"],
            )

        except NoRelevantContextError:
            # Return helpful message in appropriate language
            return AnswerResponse(
                query=payload.query,
                answer="Kechirasiz, bu ma'lumot hujjatlarda topilmadi. (Sorry, this information was not found in the documents.)",
                citations=[],
                contexts_used=0,
                confidence="low",
                retrieval_mode="none",
                chat_config={},
            )

        except LLMError as e:
            # Transaction will be rolled back automatically
            raise HTTPException(
                status_code=500, detail=f"Answer generation failed: {str(e)}"
            )

        except Exception as e:
            # Transaction will be rolled back automatically
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/{conversation_id}/message", response_model=AnswerResponse)
@rate_limit(limit=settings.RATE_LIMIT_FREE_QUERIES, scope="user")
async def send_message_with_context(
    chat_id: UUID,
    conversation_id: UUID,
    payload: AnswerRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnswerResponse:
    """
    Send message in a conversation thread (multi-turn chat).

    This endpoint:
    1. Loads conversation context (previous messages)
    2. Routes query with context awareness
    3. Retrieves relevant contexts
    4. Generates answer considering conversation history
    5. Saves both user message and assistant response

    Args:
        chat_id: Chat identifier
        conversation_id: Conversation thread identifier
        request: Answer request with query
        current_user: Authenticated user
        db: Database session

    Returns:
        Answer with citations and metadata

    Raises:
        HTTPException: 404 if conversation not found, 500 on error
    """
    import time

    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    tenant_id = current_user.tenant_id
    request.state.endpoint = "answer.multi_turn"

    # Initialize conversation service
    conversation_service = ConversationService(db)

    # Verify conversation exists
    conversation = await conversation_service.get_conversation(
        conversation_id, tenant_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.chat_id != chat_id:
        raise HTTPException(
            status_code=403, detail="Conversation not part of this chat"
        )

    async with TransactionalSession(db) as session:
        try:
            # Get conversation context
            conversation_context = await conversation_service.get_conversation_context(
                conversation_id=conversation_id, tenant_id=tenant_id, last_n=3
            )

            # Save user message
            await conversation_service.add_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                role="user",
                content=payload.query,
            )

            # Step 1: Adaptive routing
            adaptive_router = AdaptiveRouter(session)
            routing_decision = await adaptive_router.route(
                RouterRequest(query=payload.query, chat_id=str(chat_id)), tenant_id
            )

            retrieval_start = time.time()

            # Step 2: Retrieve contexts
            embedding_service = EmbeddingService()
            vector_store = QdrantVectorStore()
            tokenizer = MultilingualTokenizer()
            bm25_service = BM25Service(session, tokenizer)
            graph_service = GraphService(session)

            dense_retriever = DenseRetriever(session, embedding_service, vector_store)
            sparse_retriever = SparseRetriever(session, bm25_service)
            hybrid_retriever = HybridRetriever(
                db=session,
                dense_retriever=dense_retriever,
                sparse_retriever=sparse_retriever,
                graph_service=graph_service,
            )

            retrieval_request = RetrievalRequest(
                query=payload.query,
                mode=RetrievalMode(routing_decision.selected_mode),
                top_k=routing_decision.top_k,
                score_threshold=routing_decision.score_threshold,
                expand_with_neighbors=routing_decision.expand_with_neighbors,
                neighbor_hops=routing_decision.neighbor_hops,
            )

            contexts = await hybrid_retriever.retrieve(
                chat_id=chat_id, tenant_id=tenant_id, request=retrieval_request
            )

            retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
            generation_start = time.time()

            # Step 3: Generate answer WITH conversation context
            llm_client = OllamaClient()
            prompt_builder = PromptBuilder()
            answer_generator = AnswerGenerator(session, llm_client, prompt_builder)

            result = await answer_generator.generate_answer_with_context(
                query=payload.query,
                contexts=contexts,
                chat_id=chat_id,
                tenant_id=tenant_id,
                conversation_context=conversation_context,
            )

            generation_time_ms = int((time.time() - generation_start) * 1000)

            # Save assistant message
            await conversation_service.add_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                role="assistant",
                content=result["answer"],
                metadata={
                    "retrieval_mode": routing_decision.selected_mode,
                    "contexts_used": result["contexts_used"],
                    "confidence": result["confidence"],
                    "citations": result["citations"],
                    "retrieval_time_ms": retrieval_time_ms,
                    "generation_time_ms": generation_time_ms,
                },
            )

            return AnswerResponse(
                query=payload.query,
                answer=result["answer"],
                citations=result["citations"],
                contexts_used=result["contexts_used"],
                confidence=result["confidence"],
                retrieval_mode=routing_decision.selected_mode,
                chat_config=result["chat_config"],
            )

        except NoRelevantContextError:
            # Save "no answer" message
            no_answer = "Kechirasiz, bu ma'lumot hujjatlarda topilmadi."
            await conversation_service.add_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                role="assistant",
                content=no_answer,
            )

            return AnswerResponse(
                query=payload.query,
                answer=no_answer,
                citations=[],
                contexts_used=0,
                confidence="low",
                retrieval_mode="none",
                chat_config={},
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
@rate_limit(limit=settings.RATE_LIMIT_FREE_QUERIES, scope="user")
async def generate_answer_stream(
    chat_id: UUID,
    payload: AnswerRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Complete RAG pipeline with streaming response.

    Returns Server-Sent Events (SSE) stream with:
    1. Metadata event (retrieval info)
    2. Token events (real-time text generation)
    3. Done event (citations and confidence)

    Args:
        chat_id: Chat identifier
        request: Answer request with query
        current_user: Authenticated user
        db: Database session

    Returns:
        StreamingResponse with text/event-stream
    """

    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    tenant_id = current_user.tenant_id
    request.state.endpoint = "answer.stream"

    async def event_generator():
        """Generate SSE events."""
        try:
            # Step 1: Adaptive routing
            adaptive_router = AdaptiveRouter(db)
            routing_decision = await adaptive_router.route(
                RouterRequest(query=payload.query, chat_id=str(chat_id)), tenant_id
            )

            # Step 2: Retrieve contexts
            embedding_service = EmbeddingService()
            vector_store = QdrantVectorStore()
            tokenizer = MultilingualTokenizer()
            bm25_service = BM25Service(db, tokenizer)
            graph_service = GraphService(db)

            dense_retriever = DenseRetriever(db, embedding_service, vector_store)
            sparse_retriever = SparseRetriever(db, bm25_service)
            hybrid_retriever = HybridRetriever(
                db=db,
                dense_retriever=dense_retriever,
                sparse_retriever=sparse_retriever,
                graph_service=graph_service,
            )

            retrieval_request = RetrievalRequest(
                query=payload.query,
                mode=RetrievalMode(routing_decision.selected_mode),
                top_k=routing_decision.top_k,
                score_threshold=routing_decision.score_threshold,
                expand_with_neighbors=routing_decision.expand_with_neighbors,
                neighbor_hops=routing_decision.neighbor_hops,
            )

            contexts = await hybrid_retriever.retrieve(
                chat_id=chat_id, tenant_id=tenant_id, request=retrieval_request
            )

            # Step 3: Stream answer generation
            llm_client = OllamaClient()
            prompt_builder = PromptBuilder()
            answer_generator = AnswerGenerator(db, llm_client, prompt_builder)

            async for event in answer_generator.generate_answer_stream(
                query=payload.query,
                contexts=contexts,
                chat_id=chat_id,
                tenant_id=tenant_id,
            ):
                # Add retrieval mode to metadata event
                if event["type"] == "metadata":
                    event["retrieval_mode"] = routing_decision.selected_mode

                # Send as SSE
                yield f"data: {json.dumps(event)}\n\n"

        except NoRelevantContextError:
            # Send no context error
            error_event = {
                "type": "error",
                "message": "No relevant information found in documents",
            }
            yield f"data: {json.dumps(error_event)}\n\n"

        except Exception as e:
            # Send error event
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{conversation_id}/message/stream")
@rate_limit(limit=settings.RATE_LIMIT_FREE_QUERIES, scope="user")
async def send_message_with_context_stream(
    chat_id: UUID,
    conversation_id: UUID,
    payload: AnswerRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Send message in conversation thread with streaming response.

    This endpoint:
    1. Loads conversation context
    2. Streams answer generation in real-time
    3. Saves messages after streaming completes

    Args:
        chat_id: Chat identifier
        conversation_id: Conversation thread identifier
        request: Answer request with query
        current_user: Authenticated user
        db: Database session

    Returns:
        StreamingResponse with text/event-stream
    """
    import time

    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    tenant_id = current_user.tenant_id
    request.state.endpoint = "answer.multi_turn_stream"

    async def event_generator():
        """Generate SSE events with conversation context."""
        try:
            # Initialize conversation service
            conversation_service = ConversationService(db)

            # Verify conversation exists
            conversation = await conversation_service.get_conversation(
                conversation_id, tenant_id
            )
            if not conversation or conversation.chat_id != chat_id:
                error_event = {
                    "type": "error",
                    "message": "Conversation not found for this chat",
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                return

            # Get conversation context
            conversation_context = await conversation_service.get_conversation_context(
                conversation_id=conversation_id, tenant_id=tenant_id, last_n=3
            )

            # Save user message
            await conversation_service.add_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                role="user",
                content=payload.query,
            )

            # Step 1: Adaptive routing
            adaptive_router = AdaptiveRouter(db)
            routing_decision = await adaptive_router.route(
                RouterRequest(query=payload.query, chat_id=str(chat_id)), tenant_id
            )

            retrieval_start = time.time()

            # Step 2: Retrieve contexts
            embedding_service = EmbeddingService()
            vector_store = QdrantVectorStore()
            tokenizer = MultilingualTokenizer()
            bm25_service = BM25Service(db, tokenizer)
            graph_service = GraphService(db)

            dense_retriever = DenseRetriever(db, embedding_service, vector_store)
            sparse_retriever = SparseRetriever(db, bm25_service)
            hybrid_retriever = HybridRetriever(
                db=db,
                dense_retriever=dense_retriever,
                sparse_retriever=sparse_retriever,
                graph_service=graph_service,
            )

            retrieval_request = RetrievalRequest(
                query=payload.query,
                mode=RetrievalMode(routing_decision.selected_mode),
                top_k=routing_decision.top_k,
                score_threshold=routing_decision.score_threshold,
                expand_with_neighbors=routing_decision.expand_with_neighbors,
                neighbor_hops=routing_decision.neighbor_hops,
            )

            contexts = await hybrid_retriever.retrieve(
                chat_id=chat_id, tenant_id=tenant_id, request=retrieval_request
            )

            retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
            generation_start = time.time()

            # Step 3: Stream answer WITH conversation context
            llm_client = OllamaClient()
            prompt_builder = PromptBuilder()
            answer_generator = AnswerGenerator(db, llm_client, prompt_builder)

            full_answer = ""
            citations = []
            confidence = "low"

            async for event in answer_generator.generate_answer_stream(
                query=payload.query,
                contexts=contexts,
                chat_id=chat_id,
                tenant_id=tenant_id,
                conversation_context=conversation_context,
            ):
                # Add retrieval mode to metadata
                if event["type"] == "metadata":
                    event["retrieval_mode"] = routing_decision.selected_mode

                # Collect full answer
                if event["type"] == "token":
                    full_answer += event["content"]

                # Collect final metadata
                if event["type"] == "done":
                    citations = event.get("citations", [])
                    confidence = event.get("confidence", "low")

                # Send event
                yield f"data: {json.dumps(event)}\n\n"

            generation_time_ms = int((time.time() - generation_start) * 1000)

            # Save assistant message after streaming completes
            await conversation_service.add_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                role="assistant",
                content=full_answer,
                metadata={
                    "retrieval_mode": routing_decision.selected_mode,
                    "contexts_used": len(contexts),
                    "confidence": confidence,
                    "citations": citations,
                    "retrieval_time_ms": retrieval_time_ms,
                    "generation_time_ms": generation_time_ms,
                },
            )

        except NoRelevantContextError:
            error_event = {
                "type": "error",
                "message": "No relevant information found in documents",
            }
            yield f"data: {json.dumps(error_event)}\n\n"

        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
