"""Sliding-window API rate limiter (Phase S1-03).

Uses Redis sorted-set sliding windows when `settings.REDIS_URL` is configured,
with a thread-safe in-memory sliding-window fallback so local dev and isolated
tests enforce identical `429 Too Many Requests` + `Retry-After` semantics.
"""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from collections import deque
from typing import Any, cast

from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    """Raised when a client exceeds a sliding-window endpoint rate limit."""

    def __init__(self, retry_after_seconds: int):
        super().__init__("Too many requests. Please slow down and try again.")
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        self.error_code = "rate_limit_exceeded"


_memory_lock = threading.Lock()
_memory_windows: dict[str, deque[float]] = {}


def reset_rate_limiter_state() -> None:
    """Clears in-memory rate-limit counters (used in deterministic tests)."""
    with _memory_lock:
        _memory_windows.clear()


def _client_identifier(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


def check_sliding_window(
    bucket: str, identifier: str, limit: int, window_seconds: int
) -> None:
    """Checks and records one hit inside `(bucket, identifier)` sliding window."""
    if not settings.RATE_LIMIT_ENABLED or limit <= 0:
        return

    key = f"rl:{bucket}:{identifier}"
    now = time.time()

    if settings.REDIS_URL:
        try:
            _check_redis_sliding_window(key, now, limit, window_seconds)
            return
        except RateLimitExceededError:
            raise
        except Exception:
            logger.warning(
                "Redis rate limiter unavailable for bucket=%s; falling back to memory",
                bucket,
            )

    _check_memory_sliding_window(key, now, limit, window_seconds)


def _check_redis_sliding_window(
    key: str, now: float, limit: int, window_seconds: int
) -> None:
    import redis

    client: Any = cast(
        Any, redis.Redis.from_url(settings.REDIS_URL or "", socket_timeout=1.5)
    )
    cutoff = now - window_seconds
    member = f"{now:.6f}:{uuid.uuid4().hex[:8]}"

    pipe: Any = client.pipeline()
    pipe.zremrangebyscore(key, "-inf", cutoff)
    pipe.zcard(key)
    results = pipe.execute()
    current_count = int(results[1] or 0)

    if current_count >= limit:
        oldest = client.zrange(key, 0, 0, withscores=True)
        retry_after = window_seconds
        if oldest:
            oldest_ts = float(oldest[0][1])
            retry_after = max(1, math.ceil((oldest_ts + window_seconds) - now))
        raise RateLimitExceededError(retry_after_seconds=retry_after)

    write_pipe: Any = client.pipeline()
    write_pipe.zadd(key, {member: now})
    write_pipe.expire(key, window_seconds + 5)
    write_pipe.execute()


def _check_memory_sliding_window(
    key: str, now: float, limit: int, window_seconds: int
) -> None:
    cutoff = now - window_seconds
    with _memory_lock:
        dq = _memory_windows.setdefault(key, deque())
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= limit:
            oldest_ts = dq[0]
            retry_after = max(1, math.ceil((oldest_ts + window_seconds) - now))
            raise RateLimitExceededError(retry_after_seconds=retry_after)
        dq.append(now)


def rate_limit_upload(request: Request) -> None:
    check_sliding_window(
        "upload",
        _client_identifier(request),
        settings.RATE_LIMIT_UPLOAD_PER_MINUTE,
        settings.RATE_LIMIT_WINDOW_SECONDS,
    )


def rate_limit_prepare(request: Request) -> None:
    check_sliding_window(
        "prepare",
        _client_identifier(request),
        settings.RATE_LIMIT_PREPARE_PER_MINUTE,
        settings.RATE_LIMIT_WINDOW_SECONDS,
    )


def rate_limit_auth(request: Request) -> None:
    check_sliding_window(
        "auth",
        _client_identifier(request),
        settings.RATE_LIMIT_AUTH_PER_MINUTE,
        settings.RATE_LIMIT_WINDOW_SECONDS,
    )
