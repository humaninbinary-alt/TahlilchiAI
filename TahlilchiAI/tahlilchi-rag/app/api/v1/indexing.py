"""API endpoints for document indexing operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_chat_with_access, get_db
from app.core.auth import get_current_user
from app.core.exceptions import IndexingError
from app.models.user import User
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.indexing_service import IndexingService
from app.services.storage_service import StorageService
from app.services.vector_store import QdrantVectorStore

router = APIRouter(prefix="/chats/{chat_id}/documents", tags=["indexing"])


@router.post("/{document_id}/index", status_code=202)
async def index_document(
    chat_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Index a document into the vector store.

    This creates embeddings for all atomic units and stores them in Qdrant
    for semantic search.

    Returns 202 Accepted as indexing may take time.

    Args:
        chat_id: Chat UUID
        document_id: Document UUID
        current_user: Authenticated user (provides tenant isolation)
        db: Database session

    Returns:
        Dict with indexing statistics

    Raises:
        HTTPException: If indexing fails
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    # Initialize services
    embedding_service = EmbeddingService()
    vector_store = QdrantVectorStore()
    indexing_service = IndexingService(db, embedding_service, vector_store)

    try:
        result = await indexing_service.index_document(
            document_id=document_id, tenant_id=current_user.tenant_id, chat_id=chat_id
        )
        return result
    except IndexingError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/process-and-index", status_code=202)
async def process_and_index_document(
    chat_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Combined endpoint: Parse document AND index it.

    This is a convenience endpoint that calls both:
    1. Document processing (parse → atomic units)
    2. Indexing (embed → store in Qdrant)

    Returns 202 Accepted as processing and indexing may take time.

    Args:
        chat_id: Chat UUID
        document_id: Document UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Dict with indexing statistics

    Raises:
        HTTPException: If processing or indexing fails
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    # Step 1: Process document
    storage = StorageService()
    processor = DocumentProcessor(db, storage)

    try:
        await processor.process_document(document_id, current_user.tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    # Step 2: Index document
    embedding_service = EmbeddingService()
    vector_store = QdrantVectorStore()
    indexing_service = IndexingService(db, embedding_service, vector_store)

    try:
        result = await indexing_service.index_document(
            document_id=document_id,
            tenant_id=current_user.tenant_id,
            chat_id=chat_id,
        )
        return result
    except IndexingError as e:
        raise HTTPException(status_code=500, detail=str(e))
