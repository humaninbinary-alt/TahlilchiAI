"""Request and response schemas for hybrid retrieval system."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RetrievalMode(str, Enum):
    """Available retrieval strategies."""

    DENSE_ONLY = "dense_only"  # Vector search only
    SPARSE_ONLY = "sparse_only"  # BM25 only
    HYBRID = "hybrid"  # Dense + Sparse fusion
    GRAPH_ENHANCED = "graph_enhanced"  # Hybrid + graph expansion


class RetrievalRequest(BaseModel):
    """Request for document retrieval."""

    query: str = Field(..., min_length=1, description="Search query")
    mode: RetrievalMode = Field(
        default=RetrievalMode.HYBRID, description="Retrieval strategy"
    )
    top_k: int = Field(
        default=10, ge=1, le=50, description="Number of results to return"
    )
    score_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum relevance score"
    )
    expand_with_neighbors: bool = Field(
        default=False, description="Expand results with graph neighbors"
    )
    neighbor_hops: int = Field(
        default=1,
        ge=0,
        le=2,
        description="Number of graph hops for expansion (0 = disabled)",
    )


class RetrievedContext(BaseModel):
    """Single retrieved context unit."""

    atomic_unit_id: str
    text: str
    score: float
    source: str  # "dense", "sparse", "graph", "fusion"

    # Metadata
    document_id: str
    unit_type: str
    sequence: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None

    # Scores from different methods
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    graph_distance: Optional[int] = None


class RetrievalResponse(BaseModel):
    """Response with retrieved contexts."""

    query: str
    mode: str
    contexts: List[RetrievedContext]
    total_results: int
    retrieval_metadata: Dict[str, Any]

    class Config:
        """Pydantic configuration."""

        from_attributes = True
