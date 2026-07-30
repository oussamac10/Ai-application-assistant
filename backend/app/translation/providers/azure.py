"""Azure Translator (Text Translation API v3.0) as a `TranslationProvider`.

Talks to the REST API directly with `httpx`, matching the Phase 14 decision for
Azure Document Intelligence (ADR 0013): one small dependency-free adapter, our
own timeout and retry budget, and deterministic testability without an SDK's
object graph. See ADR 0015.

Why this API fits the pipeline built in Phase 14: `POST /translate` takes an
**array** of texts and translates all of them into the target language in one
call, and it returns the detected source language per element. So a whole
document collapses into a single request, and the forced `en -> target` path
that made a German document's labels round-trip pointlessly disappears.

Two properties get explicit enforcement here:

- **Azure answers positionally.** `translations[i]` corresponds to
  `body[i]`. That order is converted to caller ids by zipping against the
  request items, and only after verifying the element count matches. A short,
  long, or non-list response is rejected rather than partially trusted.
- **Nothing sensitive escapes.** The API key travels only in the
  `Ocp-Apim-Subscription-Key` header, never a URL or log line, and no raw
  response body or Azure error text is put into a raised message — a body can
  echo back the submitted text.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.translation.base import (
    TranslationItem,
    TranslationRequest,
    TranslationResponse,
    TranslationUsage,
)
from app.translation.errors import TranslationProviderError

logger = logging.getLogger(__name__)

# Transient conditions only. 401/403 (credentials) and 400 (malformed request)
# are never retried — that just spends the timeout budget twice.
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class AzureTranslatorProvider:
    provider_name = "azure"

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        region: str | None = None,
        api_version: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_batch_size: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = (
            endpoint if endpoint is not None else settings.AZURE_TRANSLATOR_ENDPOINT
        ).rstrip("/")
        self._api_key = (
            api_key if api_key is not None else settings.AZURE_TRANSLATOR_API_KEY
        ) or ""
        self._region = (
            region if region is not None else settings.AZURE_TRANSLATOR_REGION
        )
        self._api_version = api_version or settings.AZURE_TRANSLATOR_API_VERSION
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.AZURE_TRANSLATOR_TIMEOUT_SECONDS
        )
        self._max_retries = (
            max_retries
            if max_retries is not None
            else settings.AZURE_TRANSLATOR_MAX_RETRIES
        )
        self._max_batch_size = (
            max_batch_size
            if max_batch_size is not None
            else settings.AZURE_TRANSLATOR_MAX_BATCH_SIZE
        )
        # Injectable so tests drive a stubbed transport and never touch the
        # network.
        self._client = client

    # ------------------------------------------------------------------
    # Wire details
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": "application/json",
        }
        # A regional (non-global) resource rejects the request without this.
        if self._region:
            headers["Ocp-Apim-Subscription-Region"] = self._region
        return headers

    def _url(self, request: TranslationRequest) -> str:
        params = [
            f"api-version={self._api_version}",
            f"to={request.target_language}",
        ]
        # Omitting `from` is what enables Azure's own source-language
        # detection; it then reports what it detected per element.
        if request.source_language:
            params.append(f"from={request.source_language}")
        return f"{self._endpoint}/translate?" + "&".join(params)

    @staticmethod
    def _request_id(response: httpx.Response) -> str | None:
        request_id = response.headers.get("x-requestid") or response.headers.get(
            "apim-request-id"
        )
        return str(request_id) if request_id else None

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Maps an HTTP status onto a safe internal code.

        The body is deliberately never included: Azure echoes the submitted
        text back in some error shapes.
        """
        status = response.status_code
        if status < 400:
            return

        request_id = self._request_id(response)
        if status in (401, 403):
            raise TranslationProviderError(
                "Azure Translator rejected the configured credentials.",
                "translation_authentication_failed",
                request_id,
            )
        if status == 429:
            raise TranslationProviderError(
                "Azure Translator rate limit reached.",
                "translation_rate_limited",
                request_id,
            )
        if status in _RETRYABLE_STATUS_CODES:
            raise TranslationProviderError(
                f"Azure Translator returned a retryable HTTP {status}.",
                "translation_failed",
                request_id,
            )
        raise TranslationProviderError(
            f"Azure Translator returned HTTP {status}.",
            "translation_failed",
            request_id,
        )

    def _ensure_configured(self) -> None:
        if not settings.AZURE_TRANSLATOR_ENABLED:
            raise TranslationProviderError(
                "Azure Translator is not enabled.", "translation_not_configured"
            )
        if not self._endpoint or not self._api_key.strip():
            raise TranslationProviderError(
                "Azure Translator is not configured.", "translation_not_configured"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        if not request.items:
            return TranslationResponse(
                translations_by_id={},
                usage=TranslationUsage(
                    provider_name=self.provider_name,
                    target_language=request.target_language,
                ),
            )

        self._ensure_configured()

        translations: dict[int, str] = {}
        detected: list[str] = []
        request_ids: list[str] = []
        characters = 0
        request_count = 0
        confidences: list[float] = []
        started = time.perf_counter()

        # Azure's documented per-request limits are 1000 elements and 50,000
        # characters; chunking keeps a single call well inside both.
        items = list(request.items)
        for start in range(0, len(items), self._max_batch_size):
            chunk = tuple(items[start : start + self._max_batch_size])
            chunk_request = TranslationRequest(
                items=chunk,
                target_language=request.target_language,
                source_language=request.source_language,
                assumed_source_language=request.assumed_source_language,
            )
            payload, request_id, attempts = await self._translate_chunk(chunk_request)
            request_count += attempts
            if request_id:
                request_ids.append(request_id)

            chunk_translations, chunk_detected, chunk_confidences = (
                self._map_positional(payload, chunk, request.target_language)
            )
            translations.update(chunk_translations)
            detected.extend(chunk_detected)
            confidences.extend(chunk_confidences)
            characters += sum(len(item.text) for item in chunk)

        latency = time.perf_counter() - started
        logger.info(
            "Azure Translator: target_language=%s requested=%d returned=%d "
            "requests=%d characters=%d detected=%s latency=%.2fs",
            request.target_language,
            len(items),
            len(translations),
            request_count,
            characters,
            ",".join(sorted(set(detected))) or "-",
            latency,
        )

        return TranslationResponse(
            translations_by_id=translations,
            usage=TranslationUsage(
                provider_name=self.provider_name,
                target_language=request.target_language,
                request_count=request_count,
                translated_character_count=characters,
                latency_seconds=latency,
                detected_source_languages=tuple(sorted(set(detected))),
                detection_confidence=(min(confidences) if confidences else None),
                request_ids=tuple(request_ids),
            ),
        )

    async def _translate_chunk(
        self, request: TranslationRequest
    ) -> tuple[Any, str | None, int]:
        """One chunk, with at most `max_retries` extra attempts for transient
        failures. Returns the parsed body, the request id, and how many HTTP
        calls were actually made (so usage metrics count retries honestly)."""
        body = [{"Text": item.text} for item in request.items]
        url = self._url(request)
        attempts = 0
        last_error: TranslationProviderError | None = None

        while attempts <= self._max_retries:
            attempts += 1
            try:
                response = await self._post(url, body)
                self._raise_for_status(response)
                try:
                    return response.json(), self._request_id(response), attempts
                except ValueError as exc:
                    raise TranslationProviderError(
                        "Azure Translator returned a non-JSON response.",
                        "translation_invalid_response",
                        self._request_id(response),
                    ) from exc
            except TranslationProviderError as exc:
                last_error = exc
                if not exc.is_retryable or attempts > self._max_retries:
                    raise
                logger.warning(
                    "Azure Translator attempt %d/%d failed (%s); retrying",
                    attempts,
                    self._max_retries + 1,
                    exc.error_code,
                )

        raise last_error or TranslationProviderError(
            "Azure Translator could not be reached.", "translation_failed"
        )

    async def _post(self, url: str, body: list[dict[str, str]]) -> httpx.Response:
        timeout = httpx.Timeout(float(self._timeout_seconds))
        try:
            if self._client is not None:
                return await self._client.post(
                    url, json=body, headers=self._headers(), timeout=timeout
                )
            async with httpx.AsyncClient(timeout=timeout) as client:
                return await client.post(url, json=body, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise TranslationProviderError(
                "Azure Translator did not respond in time.", "translation_timeout"
            ) from exc
        except httpx.HTTPError as exc:
            # Transport-level failure. The exception is not chained into the
            # message: it can contain the full request URL.
            raise TranslationProviderError(
                "Azure Translator could not be reached.", "translation_failed"
            ) from exc

    def _map_positional(
        self,
        payload: Any,
        items: tuple[Any, ...],
        target_language: str,
    ) -> tuple[dict[int, str], list[str], list[float]]:
        """Converts Azure's positional response into caller ids.

        Azure guarantees `payload[i]` corresponds to `body[i]`, but that
        guarantee is verified rather than assumed: a response that is not a
        list, or whose length differs from the request, is rejected outright
        because a length mismatch means every subsequent element would be
        attributed to the wrong field.
        """
        if not isinstance(payload, list):
            raise TranslationProviderError(
                "Azure Translator returned an unexpected response shape.",
                "translation_invalid_response",
            )
        if len(payload) != len(items):
            raise TranslationProviderError(
                f"Azure Translator returned {len(payload)} results for "
                f"{len(items)} inputs.",
                "translation_invalid_response",
            )

        translations: dict[int, str] = {}
        detected: list[str] = []
        confidences: list[float] = []

        for item, entry in zip(items, payload, strict=True):
            if not isinstance(entry, dict):
                continue

            language, confidence = self._read_detection(entry)
            if language:
                detected.append(language)
            if confidence is not None:
                confidences.append(confidence)

            text = self._read_translation(entry, target_language)
            # A blank or missing translation is left out, so the caller
            # recovers exactly that item instead of storing an empty label.
            if text:
                translations[item.id] = text

        return translations, detected, confidences

    @staticmethod
    def _read_detection(entry: dict[str, Any]) -> tuple[str | None, float | None]:
        detected = entry.get("detectedLanguage")
        if not isinstance(detected, dict):
            return None, None
        language = detected.get("language")
        score = detected.get("score")
        confidence = (
            float(score)
            if isinstance(score, (int, float)) and not isinstance(score, bool)
            else None
        )
        return (str(language) if language else None), confidence

    @staticmethod
    def _read_translation(entry: dict[str, Any], target_language: str) -> str | None:
        """Picks this entry's translation.

        Azure returns a list because one request may target several languages.
        The one matching `target_language` is preferred; a single unlabelled
        result is accepted as a fallback, but an entry carrying *only* other
        languages is rejected rather than guessed at.
        """
        results = entry.get("translations")
        if not isinstance(results, list) or not results:
            return None

        wanted = target_language.lower()
        for result in results:
            if not isinstance(result, dict):
                continue
            language = str(result.get("to") or "").lower()
            if language == wanted or language.split("-")[0] == wanted.split("-")[0]:
                text = result.get("text")
                return str(text).strip() if isinstance(text, str) else None

        if len(results) == 1 and isinstance(results[0], dict):
            if not results[0].get("to"):
                text = results[0].get("text")
                return str(text).strip() if isinstance(text, str) else None
        return None

    async def health_check(self) -> bool:
        """Configuration plus one trivial round trip. Uses a fixed literal so
        no document text is ever sent for a health probe."""
        try:
            self._ensure_configured()
        except TranslationProviderError:
            return False
        try:
            result = await self.translate_batch(
                TranslationRequest(
                    items=(TranslationItem(id=0, text="ok"),),
                    target_language="de",
                    source_language="en",
                )
            )
        except TranslationProviderError:
            return False
        return bool(result.translations_by_id)
