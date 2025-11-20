"""Business logic for document upload and management."""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.storage_service import StorageService

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

# Allowed file types
ALLOWED_FILE_TYPES = ["pdf", "docx", "doc", "txt"]


class DocumentService:
    """Handles document upload and metadata management."""

    def __init__(self, db: AsyncSession, storage: StorageService):
        """
        Initialize DocumentService.

        Args:
            db: Async database session
            storage: Storage service for file management
        """
        self.db = db
        self.storage = storage

    async def upload_document(
        self, tenant_id: UUID, chat_id: UUID, user_id: UUID, file: UploadFile
    ) -> Document:
        """
        Upload a document to a chat's knowledge base.

        Steps:
        1. Validate file type (pdf, docx, txt only)
        2. Validate file size (max 50MB)
        3. Read file content
        4. Save to storage
        5. Create Document record in DB (status="uploaded")
        6. Return Document

        Args:
            tenant_id: Tenant ID for isolation
            chat_id: Chat ID the document belongs to
            user_id: User ID uploading the document
            file: Uploaded file

        Returns:
            Document: Created document instance

        Raises:
            ValueError: If file type or size is invalid
        """
        # Validate file type
        if not file.filename:
            raise ValueError("Filename is required")

        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if file_ext not in ALLOWED_FILE_TYPES:
            raise ValueError(
                f"Unsupported file type: {file_ext}. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        if file_size == 0:
            raise ValueError("File is empty")

        # Generate document ID
        doc_id = uuid4()

        # Save file to storage
        file_path = self.storage.save_file(
            tenant_id=tenant_id,
            chat_id=chat_id,
            file_id=doc_id,
            file_content=content,
            filename=file.filename,
        )

        # Create Document record
        doc = Document(
            id=doc_id,
            tenant_id=tenant_id,
            chat_id=chat_id,
            filename=file.filename,
            file_type=file_ext,
            file_size=file_size,
            file_path=file_path,
            status="uploaded",
            uploaded_by=user_id,
        )

        # Save to database
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        return doc

    async def list_documents(
        self, tenant_id: UUID, chat_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Document], int]:
        """
        List all documents for a specific chat.

        Args:
            tenant_id: Tenant ID for isolation
            chat_id: Chat ID to list documents for
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            tuple[list[Document], int]: (documents, total_count)
        """
        # Get total count
        count_query = select(func.count(Document.id)).where(
            Document.tenant_id == tenant_id, Document.chat_id == chat_id
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated documents
        query = (
            select(Document)
            .where(Document.tenant_id == tenant_id, Document.chat_id == chat_id)
            .order_by(Document.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        documents = result.scalars().all()

        return list(documents), total

    async def get_document(
        self, tenant_id: UUID, document_id: UUID
    ) -> Optional[Document]:
        """
        Get a single document with tenant isolation.

        Args:
            tenant_id: Tenant ID for isolation
            document_id: Document ID to retrieve

        Returns:
            Optional[Document]: Document instance or None if not found
        """
        query = select(Document).where(
            Document.id == document_id, Document.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_document(self, tenant_id: UUID, document_id: UUID) -> bool:
        """
        Delete document from DB and storage.

        Args:
            tenant_id: Tenant ID for isolation
            document_id: Document ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        doc = await self.get_document(tenant_id, document_id)
        if not doc:
            return False

        # Delete from storage
        self.storage.delete_file(doc.file_path)

        # Delete from DB
        await self.db.delete(doc)
        await self.db.commit()

        return True

    async def update_processing_status(
        self,
        document_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        detected_language: Optional[str] = None,
        page_count: Optional[int] = None,
        word_count: Optional[int] = None,
    ) -> Optional[Document]:
        """
        Update document processing status and metadata.

        This will be used by background processing tasks.

        Args:
            document_id: Document ID
            status: New status (processing, indexed, failed)
            error_message: Error message if status is failed
            detected_language: Detected language code
            page_count: Number of pages (for PDFs)
            word_count: Number of words

        Returns:
            Optional[Document]: Updated document or None if not found
        """
        query = select(Document).where(Document.id == document_id)
        result = await self.db.execute(query)
        doc = result.scalar_one_or_none()

        if not doc:
            return None

        # Update fields
        doc.status = status
        if error_message:
            doc.error_message = error_message
        if detected_language:
            doc.detected_language = detected_language
        if page_count is not None:
            doc.page_count = page_count
        if word_count is not None:
            doc.word_count = word_count

        # Set processed_at timestamp if indexed or failed
        if status in ["indexed", "failed"]:
            from datetime import datetime

            doc.processed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(doc)

        return doc
