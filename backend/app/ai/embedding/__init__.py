"""Embedding package for semantic vector representations."""

from app.ai.embedding.factory import get_embedding_provider, reset_embedding_provider
from app.ai.embedding.gemini import GeminiEmbeddingProvider
from app.ai.embedding.mock import MockEmbeddingProvider
from app.ai.embedding.protocol import EmbeddingProvider
from app.ai.embedding.similarity import (
    cosine_similarity,
    normalize_vector,
    rank_by_similarity,
)

__all__ = [
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "MockEmbeddingProvider",
    "cosine_similarity",
    "get_embedding_provider",
    "normalize_vector",
    "rank_by_similarity",
    "reset_embedding_provider",
]
