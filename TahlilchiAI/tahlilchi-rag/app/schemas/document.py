"""Document upload and response Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""

    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentResponse(BaseModel):
    """Response schema for document metadata."""

    id: UUID
    tenant_id: UUID
    chat_id: UUID
    filename: str
    file_type: str
    file_size: int
    detected_language: str | None
    page_count: int | None
    word_count: int | None
    status: str
    error_message: str | None
    uploaded_at: datetime
    processed_at: datetime | None

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response schema for listing documents."""

    documents: list[DocumentResponse]
    total: int
