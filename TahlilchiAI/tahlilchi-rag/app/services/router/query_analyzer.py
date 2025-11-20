"""Query analysis for adaptive routing."""

import logging
import re
from typing import Dict, Tuple

from langdetect import LangDetectException, detect

from app.schemas.router import QueryCharacteristics, QueryLanguage, QueryType

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """
    Analyzes query characteristics to inform routing decisions.

    Detects:
    - Query type (exact reference, keyword, semantic, etc.)
    - Language
    - Presence of numbers, quotes, question words
    - Technical terms
    """

    def __init__(self) -> None:
        """Initialize the query analyzer."""
        self.logger = logger

        # Question words in different languages
        self.question_words: Dict[str, list[str]] = {
            "en": ["what", "who", "where", "when", "why", "how", "which", "whose"],
            "ru": ["что", "кто", "где", "когда", "почему", "как", "какой", "чей"],
            "uz": ["nima", "kim", "qayer", "qachon", "nega", "qanday", "qaysi"],
        }

        # Reference patterns (Article 27, Section 3, etc.)
        self.reference_patterns: list[str] = [
            r"\b[Aa]rticle\s+\d+",
            r"\b[Ss]ection\s+\d+",
            r"\b[Cc]lause\s+\d+",
            r"\b[Mm]odda\s+\d+",  # Uzbek
            r"\b[Бб]андл?\s+\d+",
            r"\b[Сс]татья\s+\d+",  # Russian
        ]

    def analyze(self, query: str) -> QueryCharacteristics:
        """
        Analyze query and return characteristics.

        Args:
            query: User query text

        Returns:
            QueryCharacteristics object with analysis results
        """
        try:
            # Basic features
            word_count = len(query.split())
            has_numbers = bool(re.search(r"\d+", query))
            has_exact_phrases = '"' in query or "'" in query

            # Detect language
            language = self._detect_language(query)

            # Detect question words
            has_question_words = self._has_question_words(query, language)

            # Detect references
            has_references = self._has_references(query)

            # Detect technical terms (simplified heuristic)
            contains_technical_terms = self._has_technical_terms(query)

            # Classify query type
            query_type, confidence = self._classify_query_type(
                query=query,
                has_references=has_references,
                has_question_words=has_question_words,
                has_numbers=has_numbers,
                word_count=word_count,
            )

            return QueryCharacteristics(
                query_type=query_type,
                language=language,
                has_numbers=has_numbers,
                has_exact_phrases=has_exact_phrases,
                has_question_words=has_question_words,
                word_count=word_count,
                contains_technical_terms=contains_technical_terms,
                confidence=confidence,
            )

        except Exception as e:
            self.logger.error(f"Query analysis failed: {e}")
            # Return default characteristics
            return QueryCharacteristics(
                query_type=QueryType.UNCLEAR,
                language=QueryLanguage.UNKNOWN,
                has_numbers=False,
                has_exact_phrases=False,
                has_question_words=False,
                word_count=len(query.split()),
                contains_technical_terms=False,
                confidence=0.0,
            )

    def _detect_language(self, query: str) -> QueryLanguage:
        """Detect query language."""
        try:
            lang_code = detect(query)
            if lang_code == "uz":
                return QueryLanguage.UZBEK
            elif lang_code == "ru":
                return QueryLanguage.RUSSIAN
            elif lang_code == "en":
                return QueryLanguage.ENGLISH
            else:
                return QueryLanguage.UNKNOWN
        except LangDetectException:
            return QueryLanguage.UNKNOWN

    def _has_question_words(self, query: str, language: QueryLanguage) -> bool:
        """Check if query contains question words."""
        query_lower = query.lower()

        # Check all language question words
        for lang_code, words in self.question_words.items():
            for word in words:
                if word in query_lower:
                    return True

        # Check for question mark
        if "?" in query:
            return True

        return False

    def _has_references(self, query: str) -> bool:
        """Check if query contains exact references (Article 27, etc.)."""
        for pattern in self.reference_patterns:
            if re.search(pattern, query):
                return True
        return False

    def _has_technical_terms(self, query: str) -> bool:
        """
        Simple heuristic for technical terms.

        Checks for:
        - CamelCase words
        - UPPERCASE words
        - Words with numbers/special chars
        """
        words = query.split()

        for word in words:
            # CamelCase
            if re.match(r"^[a-z]+[A-Z]", word):
                return True
            # All caps (but not single letter)
            if word.isupper() and len(word) > 1:
                return True
            # Contains underscore or dash
            if "_" in word or "-" in word:
                return True

        return False

    def _classify_query_type(
        self,
        query: str,
        has_references: bool,
        has_question_words: bool,
        has_numbers: bool,
        word_count: int,
    ) -> Tuple[QueryType, float]:
        """
        Classify query type with confidence score.

        Returns:
            Tuple of (QueryType, confidence)
        """
        # Exact reference (high confidence)
        if has_references:
            return QueryType.EXACT_REFERENCE, 0.9

        # Semantic question (high confidence if has question words)
        if has_question_words and word_count > 3:
            return QueryType.SEMANTIC_QUESTION, 0.85

        # Keyword search (short queries with numbers/technical terms)
        if word_count <= 3 and (has_numbers or query.isupper()):
            return QueryType.KEYWORD_SEARCH, 0.75

        # Hybrid query (longer queries without clear indicators)
        if word_count > 3:
            return QueryType.HYBRID_QUERY, 0.6

        # Unclear
        return QueryType.UNCLEAR, 0.3
