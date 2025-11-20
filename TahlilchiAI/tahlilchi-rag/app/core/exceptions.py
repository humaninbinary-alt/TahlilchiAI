"""Custom exception hierarchy for document processing."""


class DocumentProcessingError(Exception):
    """Base exception for all document processing errors."""

    pass


class UnsupportedFileTypeError(DocumentProcessingError):
    """Raised when file type is not supported for parsing."""

    pass


class FileCorruptedError(DocumentProcessingError):
    """Raised when file cannot be read or parsed due to corruption."""

    pass


class LanguageDetectionError(DocumentProcessingError):
    """Raised when language detection fails."""

    pass


class ParsingError(DocumentProcessingError):
    """Raised when document parsing fails."""

    pass


class EmbeddingError(Exception):
    """Base exception for embedding generation errors."""

    pass


class VectorStoreError(Exception):
    """Base exception for vector store operations."""

    pass


class CollectionNotFoundError(VectorStoreError):
    """Raised when Qdrant collection doesn't exist."""

    pass


class IndexingError(Exception):
    """Base exception for indexing pipeline errors."""

    pass


class BM25Error(Exception):
    """Base exception for BM25 operations."""

    pass


class BM25IndexNotFoundError(BM25Error):
    """Raised when BM25 index doesn't exist for a chat."""

    pass


class BM25BuildError(BM25Error):
    """Raised when BM25 index building fails."""

    pass


class GraphError(Exception):
    """Base exception for graph operations."""

    pass


class GraphBuildError(GraphError):
    """Raised when graph building fails."""

    pass


class GraphNotFoundError(GraphError):
    """Raised when graph doesn't exist."""

    pass


class RetrievalError(Exception):
    """Base exception for retrieval operations."""

    pass


class InvalidRetrievalModeError(RetrievalError):
    """Raised when retrieval mode is invalid."""

    pass


class NoResultsFoundError(RetrievalError):
    """Raised when no results found for query."""

    pass


class RouterError(Exception):
    """Base exception for router operations."""

    pass


class QueryAnalysisError(RouterError):
    """Raised when query analysis fails."""

    pass


class LLMError(Exception):
    """Base exception for LLM operations."""

    pass


class LLMConnectionError(LLMError):
    """Raised when cannot connect to LLM."""

    pass


class LLMGenerationError(LLMError):
    """Raised when LLM generation fails."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    pass


class NoRelevantContextError(LLMError):
    """Raised when no relevant context for strict mode."""

    pass
