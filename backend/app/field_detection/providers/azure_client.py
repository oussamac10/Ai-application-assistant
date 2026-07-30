"""Thin HTTP client for the Azure Document Intelligence "analyze" REST API.

Kept separate from the provider so normalization can be unit-tested against
recorded response payloads without any HTTP involved, and so the transport
concerns (auth header, async polling, timeout, bounded retries, error
mapping) live in exactly one place.

Why REST over the `azure-ai-documentintelligence` SDK: the repository
already depends on `httpx` for the Ollama provider, so the REST route adds
no new dependency (the project's dependency rules require justifying any
addition and prefer an existing capability). It also keeps the retry and
timeout budget under our own control and makes deterministic testing a
matter of stubbing `httpx`, exactly as the Ollama provider's tests already
do. See ADR 0013.

Security: the API key is sent only in the `Ocp-Apim-Subscription-Key`
request header. It is never logged, never placed in a URL, and never
included in a raised exception's message.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.field_detection.errors import AzureDocumentIntelligenceError

logger = logging.getLogger(__name__)

# Azure returns 202 with an Operation-Location header, then that operation
# is polled until it reports a terminal status.
_TERMINAL_SUCCESS = "succeeded"
_TERMINAL_FAILURES = ("failed", "canceled", "cancelled")

# How long to wait between polls of a running analyze operation.
_POLL_INTERVAL_SECONDS = 1.0

# Status codes worth retrying: transient server-side/throughput problems.
# 401/403 (bad credentials) and 400 (bad request) never are.
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class AzureAnalyzeResponse:
    """The `analyzeResult` payload plus the diagnostics we keep about the
    call that produced it. `analyze_result` is plain JSON — no SDK objects
    ever enter the application workflow."""

    analyze_result: dict[str, Any]
    request_id: str | None
    model_id: str
    api_version: str
    duration_seconds: float


class AzureDocumentIntelligenceClient:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model_id: str,
        api_version: str,
        timeout_seconds: int = 120,
        max_retries: int = 1,
        poll_interval_seconds: float = _POLL_INTERVAL_SECONDS,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._model_id = model_id
        self._api_version = api_version
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._poll_interval = poll_interval_seconds

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def _headers(self) -> dict[str, str]:
        return {"Ocp-Apim-Subscription-Key": self._api_key}

    def _analyze_url(self) -> str:
        return (
            f"{self._endpoint}/documentintelligence/documentModels/"
            f"{self._model_id}:analyze?api-version={self._api_version}"
        )

    @staticmethod
    def _request_id(response: httpx.Response) -> str | None:
        request_id = response.headers.get("apim-request-id") or response.headers.get(
            "x-ms-request-id"
        )
        return str(request_id) if request_id else None

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Maps an Azure HTTP status onto a safe internal error code.

        The response body is deliberately not included in the raised
        message: it can echo back parts of the submitted document.
        """
        status = response.status_code
        if status < 400:
            return

        request_id = self._request_id(response)
        if status in (401, 403):
            raise AzureDocumentIntelligenceError(
                "Azure rejected the configured credentials.",
                "azure_authentication_failed",
                request_id,
            )
        if status == 429:
            raise AzureDocumentIntelligenceError(
                "Azure rate limit reached.", "azure_rate_limited", request_id
            )
        if status in _RETRYABLE_STATUS_CODES:
            raise AzureDocumentIntelligenceError(
                f"Azure returned a retryable HTTP {status}.",
                "azure_processing_failed",
                request_id,
            )
        raise AzureDocumentIntelligenceError(
            f"Azure returned HTTP {status}.", "azure_processing_failed", request_id
        )

    @staticmethod
    def _is_retryable(error: AzureDocumentIntelligenceError) -> bool:
        return error.error_code in ("azure_rate_limited", "azure_processing_failed")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_document(self, pdf_path: Path) -> AzureAnalyzeResponse:
        """Submits a PDF, polls the resulting operation, and returns its
        `analyzeResult`. Retries only transient failures, at most
        `max_retries` extra attempts, within the overall timeout budget."""
        try:
            pdf_bytes = pdf_path.read_bytes()
        except OSError as exc:
            raise AzureDocumentIntelligenceError(
                "Unable to read the stored document for analysis.",
                "azure_processing_failed",
            ) from exc

        last_error: AzureDocumentIntelligenceError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return self._analyze_once(pdf_bytes)
            except AzureDocumentIntelligenceError as exc:
                last_error = exc
                if not self._is_retryable(exc) or attempt >= self._max_retries:
                    raise
                logger.warning(
                    "Azure analyze attempt %d/%d failed (%s); retrying",
                    attempt + 1,
                    self._max_retries + 1,
                    exc.error_code,
                )

        assert last_error is not None  # loop always raises or returns
        raise last_error

    def _analyze_once(self, pdf_bytes: bytes) -> AzureAnalyzeResponse:
        started = time.monotonic()
        deadline = started + self._timeout_seconds

        with httpx.Client(
            timeout=httpx.Timeout(float(self._timeout_seconds))
        ) as client:
            try:
                submit = client.post(
                    self._analyze_url(),
                    headers={**self._headers, "Content-Type": "application/pdf"},
                    content=pdf_bytes,
                )
            except httpx.TimeoutException as exc:
                raise AzureDocumentIntelligenceError(
                    "Azure did not respond in time.", "azure_timeout"
                ) from exc
            except httpx.HTTPError as exc:
                raise AzureDocumentIntelligenceError(
                    "Could not reach the Azure endpoint.", "azure_processing_failed"
                ) from exc

            self._raise_for_status(submit)
            request_id = self._request_id(submit)

            operation_url = submit.headers.get("operation-location")
            if not operation_url:
                raise AzureDocumentIntelligenceError(
                    "Azure did not return an operation location.",
                    "azure_invalid_response",
                    request_id,
                )

            return self._poll_operation(
                client, operation_url, request_id, started, deadline
            )

    def _poll_operation(
        self,
        client: httpx.Client,
        operation_url: str,
        submit_request_id: str | None,
        started: float,
        deadline: float,
    ) -> AzureAnalyzeResponse:
        while True:
            if time.monotonic() >= deadline:
                raise AzureDocumentIntelligenceError(
                    "Azure analysis did not complete within the timeout.",
                    "azure_timeout",
                    submit_request_id,
                )

            try:
                poll = client.get(operation_url, headers=self._headers)
            except httpx.TimeoutException as exc:
                raise AzureDocumentIntelligenceError(
                    "Azure did not respond in time.",
                    "azure_timeout",
                    submit_request_id,
                ) from exc
            except httpx.HTTPError as exc:
                raise AzureDocumentIntelligenceError(
                    "Could not reach the Azure endpoint.",
                    "azure_processing_failed",
                    submit_request_id,
                ) from exc

            self._raise_for_status(poll)
            request_id = self._request_id(poll) or submit_request_id

            try:
                payload = poll.json()
            except ValueError as exc:
                raise AzureDocumentIntelligenceError(
                    "Azure returned a non-JSON response.",
                    "azure_invalid_response",
                    request_id,
                ) from exc

            status = str(payload.get("status", "")).lower()
            if status in _TERMINAL_FAILURES:
                raise AzureDocumentIntelligenceError(
                    "Azure reported the analysis as failed.",
                    "azure_processing_failed",
                    request_id,
                )
            if status == _TERMINAL_SUCCESS:
                analyze_result = payload.get("analyzeResult")
                if not isinstance(analyze_result, dict):
                    raise AzureDocumentIntelligenceError(
                        "Azure response did not contain an analyzeResult object.",
                        "azure_invalid_response",
                        request_id,
                    )
                duration = time.monotonic() - started
                logger.info(
                    "Azure analyze completed: model=%s api_version=%s "
                    "pages=%d duration=%.2fs request_id=%s",
                    self._model_id,
                    self._api_version,
                    len(analyze_result.get("pages") or []),
                    duration,
                    request_id,
                )
                return AzureAnalyzeResponse(
                    analyze_result=analyze_result,
                    request_id=request_id,
                    model_id=self._model_id,
                    api_version=self._api_version,
                    duration_seconds=duration,
                )

            time.sleep(self._poll_interval)
