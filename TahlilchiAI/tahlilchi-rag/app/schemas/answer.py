"""Request and response schemas for answer generation."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    """Request for answer generation."""

    query: str = Field(..., min_length=1, description="User's question")


class Citation(BaseModel):
    """Citation/source reference."""

    type: str  # "document", "context"
    document: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    context_number: Optional[int] = None
    text: Optional[str] = None


class AnswerResponse(BaseModel):
    """Response with generated answer."""

    query: str
    answer: str
    citations: List[Citation]
    contexts_used: int
    confidence: str  # high, medium, low

    # Metadata
    retrieval_mode: str
    chat_config: Dict[str, Any]
