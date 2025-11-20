"""Schemas for adaptive query router."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Types of queries detected."""

    EXACT_REFERENCE = "exact_reference"  # "Article 27", "Section 5"
    KEYWORD_SEARCH = "keyword_search"  # Technical terms, IDs
    SEMANTIC_QUESTION = "semantic_question"  # "What is...", "How to..."
    HYBRID_QUERY = "hybrid_query"  # Mix of keywords and semantics
    UNCLEAR = "unclear"  # Can't determine


class QueryLanguage(str, Enum):
    """Detected query language."""

    UZBEK = "uz"
    RUSSIAN = "ru"
    ENGLISH = "en"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class QueryCharacteristics(BaseModel):
    """Analysis of query characteristics."""

    query_type: QueryType
    language: QueryLanguage
    has_numbers: bool
    has_exact_phrases: bool  # Quoted phrases
    has_question_words: bool  # who, what, where, when, why, how
    word_count: int
    contains_technical_terms: bool
    confidence: float  # 0-1, confidence in classification


class RoutingDecision(BaseModel):
    """Router's decision on retrieval strategy."""

    selected_mode: str  # dense_only, sparse_only, hybrid, graph_enhanced
    top_k: int
    score_threshold: float
    expand_with_neighbors: bool
    neighbor_hops: int

    # Explanation
    reasoning: str
    query_characteristics: QueryCharacteristics

    # Configuration influence
    chat_strictness: str
    chat_purpose: str


class RouterRequest(BaseModel):
    """Request for routing decision."""

    query: str = Field(..., min_length=1)
    chat_id: str

    # Optional overrides
    force_mode: Optional[str] = None
    force_top_k: Optional[int] = None
