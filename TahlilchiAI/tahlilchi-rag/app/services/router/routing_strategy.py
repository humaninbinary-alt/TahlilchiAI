"""Routing strategy selection based on query characteristics."""

import logging
from typing import Any, Dict

from app.schemas.retrieval import RetrievalMode
from app.schemas.router import QueryCharacteristics, QueryType, RoutingDecision

logger = logging.getLogger(__name__)


class RoutingStrategy:
    """
    Selects optimal retrieval strategy based on query characteristics and chat configuration.

    Rules-based approach (no ML needed for MVP).
    """

    def __init__(self) -> None:
        """Initialize the routing strategy."""
        self.logger = logger

    def decide(
        self, query_chars: QueryCharacteristics, chat_config: Dict[str, Any]
    ) -> RoutingDecision:
        """
        Make routing decision.

        Args:
            query_chars: Query characteristics from analyzer
            chat_config: Chat configuration (strictness, purpose, etc.)

        Returns:
            RoutingDecision with selected strategy and parameters
        """
        # Extract chat config
        strictness = chat_config.get("strictness", "strict_docs_only")
        purpose = chat_config.get("purpose", "general")

        # Decision logic based on query type
        if query_chars.query_type == QueryType.EXACT_REFERENCE:
            return self._handle_exact_reference(query_chars, strictness, purpose)

        elif query_chars.query_type == QueryType.KEYWORD_SEARCH:
            return self._handle_keyword_search(query_chars, strictness, purpose)

        elif query_chars.query_type == QueryType.SEMANTIC_QUESTION:
            return self._handle_semantic_question(query_chars, strictness, purpose)

        elif query_chars.query_type == QueryType.HYBRID_QUERY:
            return self._handle_hybrid_query(query_chars, strictness, purpose)

        else:  # UNCLEAR
            return self._handle_unclear(query_chars, strictness, purpose)

    def _handle_exact_reference(
        self, query_chars: QueryCharacteristics, strictness: str, purpose: str
    ) -> RoutingDecision:
        """
        Handle exact references (Article 27, Section 5).

        Strategy: sparse (for exact match) + graph (for structure)
        """
        return RoutingDecision(
            selected_mode=RetrievalMode.GRAPH_ENHANCED.value,
            top_k=10,
            score_threshold=0.2,  # Lower threshold for exact matches
            expand_with_neighbors=True,
            neighbor_hops=2,  # Get more context around reference
            reasoning=(
                "Detected exact reference (article/section number). "
                "Using graph-enhanced mode to find the reference and surrounding context."
            ),
            query_characteristics=query_chars,
            chat_strictness=strictness,
            chat_purpose=purpose,
        )

    def _handle_keyword_search(
        self, query_chars: QueryCharacteristics, strictness: str, purpose: str
    ) -> RoutingDecision:
        """
        Handle keyword searches (short, technical terms).

        Strategy: sparse (BM25) for exact keyword matching
        """
        return RoutingDecision(
            selected_mode=RetrievalMode.SPARSE_ONLY.value,
            top_k=15,
            score_threshold=0.0,  # BM25 has its own relevance
            expand_with_neighbors=False,
            neighbor_hops=0,
            reasoning=(
                "Detected keyword search (short query with technical terms). "
                "Using BM25 sparse search for exact keyword matching."
            ),
            query_characteristics=query_chars,
            chat_strictness=strictness,
            chat_purpose=purpose,
        )

    def _handle_semantic_question(
        self, query_chars: QueryCharacteristics, strictness: str, purpose: str
    ) -> RoutingDecision:
        """
        Handle semantic questions (What is..., How to...).

        Strategy: hybrid (dense + sparse) for best semantic understanding
        """
        # Adjust based on strictness
        if strictness == "strict_docs_only":
            top_k = 8
            threshold = 0.4  # Higher threshold for strict mode
        else:
            top_k = 12
            threshold = 0.3

        return RoutingDecision(
            selected_mode=RetrievalMode.HYBRID.value,
            top_k=top_k,
            score_threshold=threshold,
            expand_with_neighbors=True,
            neighbor_hops=1,
            reasoning=(
                "Detected semantic question. "
                "Using hybrid mode (dense + sparse) for best semantic understanding."
            ),
            query_characteristics=query_chars,
            chat_strictness=strictness,
            chat_purpose=purpose,
        )

    def _handle_hybrid_query(
        self, query_chars: QueryCharacteristics, strictness: str, purpose: str
    ) -> RoutingDecision:
        """
        Handle hybrid queries (mix of keywords and semantics).

        Strategy: hybrid mode (the default)
        """
        return RoutingDecision(
            selected_mode=RetrievalMode.HYBRID.value,
            top_k=10,
            score_threshold=0.35,
            expand_with_neighbors=False,
            neighbor_hops=0,
            reasoning=(
                "General query with mixed characteristics. "
                "Using hybrid mode (dense + sparse fusion) for balanced results."
            ),
            query_characteristics=query_chars,
            chat_strictness=strictness,
            chat_purpose=purpose,
        )

    def _handle_unclear(
        self, query_chars: QueryCharacteristics, strictness: str, purpose: str
    ) -> RoutingDecision:
        """
        Handle unclear queries.

        Strategy: default to hybrid (safest option)
        """
        return RoutingDecision(
            selected_mode=RetrievalMode.HYBRID.value,
            top_k=10,
            score_threshold=0.3,
            expand_with_neighbors=False,
            neighbor_hops=0,
            reasoning=(
                "Query type unclear. " "Using hybrid mode as default safe strategy."
            ),
            query_characteristics=query_chars,
            chat_strictness=strictness,
            chat_purpose=purpose,
        )
