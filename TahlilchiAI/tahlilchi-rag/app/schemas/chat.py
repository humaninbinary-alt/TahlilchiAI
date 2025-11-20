"""Chat configuration Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatCreateRequest(BaseModel):
    """Request schema for creating a new chat."""

    name: str = Field(..., min_length=1, max_length=255, description="Chat name")
    purpose: str = Field(
        ...,
        description="Chat purpose (hr_assistant, policy_qa, sop_helper, product_docs, etc.)",
    )
    target_audience: str = Field(
        "staff",
        description="Target audience (managers, staff, specialists, public)",
    )
    tone: str = Field(
        ...,
        description="Response tone (simple_uzbek, technical_russian, formal_english, etc.)",
    )
    strictness: str = Field(
        ..., description="Response strictness (strict_docs_only, allow_reasoning)"
    )
    sensitivity: str = Field(
        "medium", description="Data sensitivity (high_on_prem, medium, low)"
    )
    document_types: list[str] = Field(
        default_factory=list,
        description="Document types (policies, contracts, manuals, etc.)",
    )
    document_languages: list[str] = Field(
        default_factory=list, description="Document languages (uz, ru, en)"
    )

    # Optional RAG configuration overrides
    embedding_model: str | None = Field(
        None, description="Override default embedding model"
    )
    llm_model: str | None = Field(None, description="Override default LLM model")
    retrieval_strategy: str | None = Field(
        None,
        description="Override default retrieval strategy (hybrid, dense_only, graph_priority)",
    )
    max_context_chunks: int | None = Field(
        None, ge=1, le=50, description="Override max context chunks"
    )


class ChatUpdateRequest(BaseModel):
    """Request schema for updating a chat (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    tone: str | None = None
    strictness: str | None = None
    sensitivity: str | None = None
    document_types: list[str] | None = None
    document_languages: list[str] | None = None
    embedding_model: str | None = None
    llm_model: str | None = None
    retrieval_strategy: str | None = None
    max_context_chunks: int | None = Field(None, ge=1, le=50)
    is_active: bool | None = None


class ChatResponse(BaseModel):
    """Response schema for chat configuration."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    purpose: str
    target_audience: str
    tone: str
    strictness: str
    sensitivity: str
    document_types: list[str]
    document_languages: list[str]
    embedding_model: str
    llm_model: str
    retrieval_strategy: str
    max_context_chunks: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        """Pydantic config."""

        from_attributes = True  # For SQLAlchemy models


class ChatListResponse(BaseModel):
    """Response schema for listing chats."""

    chats: list[ChatResponse]
    total: int
