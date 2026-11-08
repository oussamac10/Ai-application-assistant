"""Gemini embedding provider using Google text-embedding-004.

Design rules:
- Uses httpx.AsyncClient directly (no vendor SDK dependencies).
- Passes API key via 'x-goog-api-key' header (never query string).
- In-memory cache for repeated text strings.
- Graceful error handling with retries on transient errors.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.ai.embedding.similarity import normalize_vector
from app.ai.errors import (
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)

logger = logging.getLogger(__name__)

_DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 0.5


class GeminiEmbeddingProvider:
    """Generates dense vector embeddings using Google text-embedding-004."""

    DIMENSIONS: int = 768

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_EMBEDDING_MODEL,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout)
        self._client = client or httpx.AsyncClient(timeout=self._timeout)
        self._cache: dict[str, list[float]] = {}

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS

    async def get_embedding(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            return [0.0] * self.DIMENSIONS

        if cleaned in self._cache:
            return self._cache[cleaned]

        url = f"{self._base_url}/models/{self._model}:embedContent"
        payload = {
            "model": f"models/{self._model}",
            "content": {
                "parts": [{"text": cleaned}],
            },
        }

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self._api_key,
                    },
                )

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    wait = _BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "Gemini embedding API returned status %d on attempt %d; retrying in %.1fs",
                        response.status_code,
                        attempt + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code != 200:
                    raise AIProviderUnavailableError(
                        f"Gemini embedding API returned status {response.status_code}: {response.text[:200]}"
                    )

                data: dict[str, Any] = response.json()
                values = data.get("embedding", {}).get("values", [])
                if not values:
                    raise AIProviderUnavailableError(
                        "Gemini embedding API returned empty vector"
                    )

                norm_vec = normalize_vector(values)
                self._cache[cleaned] = norm_vec
                return norm_vec

            except httpx.TimeoutException as exc:
                last_error = exc
                wait = _BASE_BACKOFF_SECONDS * (2**attempt)
                await asyncio.sleep(wait)
            except Exception as exc:
                last_error = exc
                break

        if isinstance(last_error, httpx.TimeoutException):
            raise AIProviderTimeoutError(
                "Gemini embedding request timed out"
            ) from last_error
        raise AIProviderUnavailableError(
            f"Gemini embedding failed: {last_error}"
        ) from last_error

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        # Batch with parallel execution over individual cached calls
        return await asyncio.gather(*(self.get_embedding(t) for t in texts))
