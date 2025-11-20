"""Embedding generation service using multilingual-e5-large model."""

import logging
from typing import List, Optional

import torch
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using multilingual-e5-large.

    This model supports Uzbek, Russian, and English with strong performance.
    Embedding dimension: 1024

    The service uses lazy loading for the model and supports both single
    and batch embedding generation.
    """

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        """
        Initialize embedding service.

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model: Optional[SentenceTransformer] = None
        self.logger = logger

    @property
    def model(self) -> SentenceTransformer:
        """
        Lazy load model on first use.

        Returns:
            Loaded SentenceTransformer model

        Raises:
            EmbeddingError: If model loading fails
        """
        if self._model is None:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            try:
                self._model = SentenceTransformer(self.model_name)
                # Use GPU if available
                if torch.cuda.is_available():
                    self._model = self._model.to("cuda")
                    self.logger.info("Using GPU for embeddings")
                else:
                    self.logger.info("Using CPU for embeddings")
            except Exception as e:
                self.logger.error(f"Failed to load embedding model: {e}")
                raise EmbeddingError(f"Cannot load model {self.model_name}: {e}")
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            List of floats (dimension: 1024)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            # Add instruction prefix for better retrieval performance
            # (recommended by multilingual-e5 authors)
            prefixed_text = f"passage: {text}"
            embedding = self.model.encode(prefixed_text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts

        Returns:
            List of embeddings (each embedding is List[float])

        Raises:
            EmbeddingError: If batch embedding fails
        """
        if not texts:
            return []

        try:
            # Add prefix to all texts
            prefixed_texts = [f"passage: {text}" for text in texts]

            self.logger.info(f"Embedding batch of {len(texts)} texts")
            embeddings = self.model.encode(
                prefixed_texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embeddings.tolist()
        except Exception as e:
            self.logger.error(f"Batch embedding failed: {e}")
            raise EmbeddingError(f"Failed to embed batch: {e}")

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Note: Uses different prefix than documents for better retrieval
        (asymmetric retrieval).

        Args:
            query: Search query text

        Returns:
            Query embedding (List[float])

        Raises:
            EmbeddingError: If query embedding fails
        """
        try:
            # Use "query:" prefix for queries (asymmetric retrieval)
            prefixed_query = f"query: {query}"
            embedding = self.model.encode(prefixed_query, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            self.logger.error(f"Query embedding failed: {e}")
            raise EmbeddingError(f"Failed to embed query: {e}")
