"""Simple in-memory response cache for AI provider results.

The cache is disabled by default (OLLAMA_CACHE_ENABLED=false).
When enabled, it stores extracted values for the lifetime of the process.
No persistence; the cache is cleared on restart.

Privacy note: cached values contain normalised form-field content.
Only enable caching when the privacy implications are understood and accepted.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AIResponseCache:
    """Process-level in-memory cache for AI extraction responses.

    The cache key is a SHA-256 hash of the serialised request parameters.
    Cache entries live for the entire process lifetime.
    """

    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled
        self._store: dict[str, Any] = {}

    def _make_key(self, data: dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, data: dict[str, Any]) -> Any | None:
        if not self._enabled:
            return None
        key = self._make_key(data)
        return self._store.get(key)

    def set(self, data: dict[str, Any], value: Any) -> None:
        if not self._enabled:
            return
        key = self._make_key(data)
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()
        logger.info("AI response cache cleared")

    @property
    def size(self) -> int:
        return len(self._store)
