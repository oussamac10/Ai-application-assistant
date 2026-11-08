"""Embedding provider protocol definition.

Defines the contract for text embedding generation across cloud and test providers.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for generating dense semantic vector embeddings from text."""

    @property
    def dimensions(self) -> int:
        """The dimensionality of vectors returned by this provider."""
        ...

    async def get_embedding(self, text: str) -> list[float]:
        """Generates a normalized embedding vector for a single string.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the dense semantic vector.
        """
        ...

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates normalized embedding vectors for multiple strings in batch.

        Args:
            texts: List of strings to embed.

        Returns:
            List of float vectors, one for each input text in corresponding order.
        """
        ...
