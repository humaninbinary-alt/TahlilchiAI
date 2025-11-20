"""Document upload and management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_chat_with_access, get_db
from app.config import settings
from app.core.auth import get_current_user
from app.core.decorators import rate_limit
from app.models.job import Job
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.schemas.job import JobCreate
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService
from app.tasks.document_tasks import process_and_index_document_task

router = APIRouter(prefix="/chats/{chat_id}/documents", tags=["documents"])


@router.post("/", response_model=DocumentUploadResponse, status_code=201)
@rate_limit(limit=settings.RATE_LIMIT_FREE_UPLOADS, scope="user")
async def upload_document(
    request: Request,
    chat_id: UUID,
    file: UploadFile = File(
        ..., description="Document file to upload (PDF, DOCX, TXT)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document to a chat's knowledge base.

    Accepts PDF, DOCX, DOC, and TXT files up to 50MB.
    The file is saved to disk and metadata is stored in the database.

    Args:
        chat_id: Chat ID to upload document to
        file: Uploaded file
        current_user: Authenticated user (provides tenant/user IDs)
        db: Database session

    Returns:
        DocumentUploadResponse: Upload confirmation with document metadata

    Raises:
        HTTPException: 400 if file type/size is invalid
    """
    request.state.endpoint = "documents.upload"

    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    storage = StorageService()
    service = DocumentService(db, storage)

    try:
        document = await service.upload_document(
            tenant_id=current_user.tenant_id,
            chat_id=chat_id,
            user_id=current_user.id,
            file=file,
        )
        return DocumentUploadResponse.model_validate(document)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    chat_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=100, description="Maximum number of records to return"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all documents in a chat.

    Returns a paginated list of all documents uploaded to the specified chat.

    Args:
        chat_id: Chat ID to list documents for
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user
        db: Database session

    Returns:
        DocumentListResponse: List of documents and total count
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    storage = StorageService()
    service = DocumentService(db, storage)

    documents, total = await service.list_documents(
        tenant_id=current_user.tenant_id,
        chat_id=chat_id,
        skip=skip,
        limit=limit,
    )

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents], total=total
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    chat_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get document metadata.

    Retrieves detailed metadata for a specific document.

    Args:
        chat_id: Chat ID (for URL consistency, not used in query due to tenant isolation)
        document_id: Document ID to retrieve
        current_user: Authenticated user
        db: Database session

    Returns:
        DocumentResponse: Document metadata

    Raises:
        HTTPException: 404 if document not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    storage = StorageService()
    service = DocumentService(db, storage)

    document = await service.get_document(current_user.tenant_id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    chat_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document.

    Deletes the document from both the database and file storage.

    Args:
        chat_id: Chat ID (for URL consistency, not used in query due to tenant isolation)
        document_id: Document ID to delete
        current_user: Authenticated user
        db: Database session

    Returns:
        None: 204 No Content on success

    Raises:
        HTTPException: 404 if document not found
    """
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    storage = StorageService()
    service = DocumentService(db, storage)

    success = await service.delete_document(current_user.tenant_id, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return None


@router.post("/{document_id}/process", response_model=JobCreate, status_code=202)
@rate_limit(limit=settings.RATE_LIMIT_FREE_UPLOADS, scope="user")
async def process_document(
    chat_id: UUID,
    document_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobCreate:
    """
    Trigger document processing (parse + index) as background job.

    This endpoint initiates the document processing pipeline which:
    1. Parses the document into atomic units
    2. Generates embeddings
    3. Indexes in Qdrant vector store
    4. Builds BM25 index
    5. Constructs knowledge graph

    Processing happens asynchronously via Celery. Use the returned job_id
    to poll for status at GET /jobs/{job_id}/status

    Args:
        chat_id: Chat ID for the document
        document_id: Document ID to process
        current_user: Authenticated user
        db: Database session

    Returns:
        JobCreate: Job ID and status message

    Raises:
        HTTPException: 404 if document not found
    """
    request.state.endpoint = "documents.process"

    # Verify document exists
    await get_chat_with_access(
        chat_id=chat_id,
        tenant_id=current_user.tenant_id,
        db=db,
        user=current_user,
    )

    storage = StorageService()
    service = DocumentService(db, storage)
    document = await service.get_document(current_user.tenant_id, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.chat_id != chat_id:
        raise HTTPException(
            status_code=403, detail="Document does not belong to this chat"
        )

    # Trigger background task
    task = process_and_index_document_task.delay(
        document_id=str(document_id),
        tenant_id=str(current_user.tenant_id),
        chat_id=str(chat_id),
    )

    # Create job record
    job = Job(
        id=task.id,
        tenant_id=current_user.tenant_id,
        chat_id=chat_id,
        created_by=current_user.id,
        task_name="process_and_index_document",
        status="pending",
        progress=0,
    )
    db.add(job)
    await db.commit()

    return JobCreate(
        job_id=task.id,
        message="Document processing started. Use job_id to check status.",
    )
