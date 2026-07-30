"""Transport-level tests for AzureDocumentIntelligenceClient.

All HTTP is mocked — no test in this repository ever contacts the real
Azure service (see docs/testing.md's "no paid provider in automated tests"
rule, which this phase extends to Azure).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.field_detection.errors import AzureDocumentIntelligenceError
from app.field_detection.providers.azure_client import (
    AzureDocumentIntelligenceClient,
)

_API_KEY = "super-secret-key-value"
_OPERATION_URL = "https://example.cognitiveservices.azure.com/operations/abc"


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    return path


def make_client(**overrides: Any) -> AzureDocumentIntelligenceClient:
    kwargs: dict[str, Any] = {
        "endpoint": "https://example.cognitiveservices.azure.com",
        "api_key": _API_KEY,
        "model_id": "prebuilt-layout",
        "api_version": "2024-11-30",
        "timeout_seconds": 5,
        "max_retries": 1,
        "poll_interval_seconds": 0.0,
    }
    kwargs.update(overrides)
    return AzureDocumentIntelligenceClient(**kwargs)


def _submit_response(status: int = 202, operation: str | None = _OPERATION_URL):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"apim-request-id": "req-1"}
    if operation:
        resp.headers["operation-location"] = operation
    return resp


def _poll_response(status_value: str, analyze_result: dict[str, Any] | None = None):
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"apim-request-id": "req-1"}
    payload: dict[str, Any] = {"status": status_value}
    if analyze_result is not None:
        payload["analyzeResult"] = analyze_result
    resp.json.return_value = payload
    return resp


def test_successful_analysis_polls_until_succeeded(pdf: Path) -> None:
    client = make_client()
    analyze_result = {"pages": [{"pageNumber": 1}], "modelId": "prebuilt-layout"}

    with (
        patch("httpx.Client.post", return_value=_submit_response()),
        patch(
            "httpx.Client.get",
            side_effect=[
                _poll_response("running"),
                _poll_response("succeeded", analyze_result),
            ],
        ) as mock_get,
    ):
        result = client.analyze_document(pdf)

    assert result.analyze_result == analyze_result
    assert result.request_id == "req-1"
    assert result.model_id == "prebuilt-layout"
    assert mock_get.call_count == 2


def test_api_key_is_sent_as_a_header_and_never_in_the_url(pdf: Path) -> None:
    client = make_client()
    captured: dict[str, Any] = {}

    def _capture_post(self: Any, url: str, **kwargs: Any):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers", {})
        return _submit_response()

    with (
        patch("httpx.Client.post", new=_capture_post),
        patch(
            "httpx.Client.get", return_value=_poll_response("succeeded", {"pages": []})
        ),
    ):
        client.analyze_document(pdf)

    assert _API_KEY not in captured["url"]
    assert captured["headers"]["Ocp-Apim-Subscription-Key"] == _API_KEY


def test_authentication_failure_is_not_retried(pdf: Path) -> None:
    client = make_client(max_retries=3)
    with patch(
        "httpx.Client.post", return_value=_submit_response(status=401)
    ) as mock_post:
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_authentication_failed"
    # A bad key will never succeed on retry, so exactly one attempt.
    assert mock_post.call_count == 1


def test_rate_limit_is_retried_then_surfaces_its_own_code(pdf: Path) -> None:
    client = make_client(max_retries=1)
    with patch(
        "httpx.Client.post", return_value=_submit_response(status=429)
    ) as mock_post:
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_rate_limited"
    assert mock_post.call_count == 2  # initial + one bounded retry


def test_transient_server_error_recovers_on_retry(pdf: Path) -> None:
    client = make_client(max_retries=1)
    with (
        patch(
            "httpx.Client.post",
            side_effect=[_submit_response(status=503), _submit_response()],
        ),
        patch(
            "httpx.Client.get", return_value=_poll_response("succeeded", {"pages": []})
        ),
    ):
        result = client.analyze_document(pdf)

    assert result.analyze_result == {"pages": []}


def test_request_timeout_maps_to_azure_timeout(pdf: Path) -> None:
    client = make_client(max_retries=0)
    with patch(
        "httpx.Client.post",
        side_effect=httpx.ReadTimeout("timed out", request=MagicMock()),
    ):
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_timeout"


def test_operation_never_completing_hits_the_timeout_budget(pdf: Path) -> None:
    client = make_client(timeout_seconds=0, max_retries=0)
    with (
        patch("httpx.Client.post", return_value=_submit_response()),
        patch("httpx.Client.get", return_value=_poll_response("running")),
    ):
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_timeout"


def test_missing_operation_location_is_an_invalid_response(pdf: Path) -> None:
    client = make_client(max_retries=0)
    with patch("httpx.Client.post", return_value=_submit_response(operation=None)):
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_invalid_response"


def test_failed_operation_status_maps_to_processing_failed(pdf: Path) -> None:
    client = make_client(max_retries=0)
    with (
        patch("httpx.Client.post", return_value=_submit_response()),
        patch("httpx.Client.get", return_value=_poll_response("failed")),
    ):
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_processing_failed"


def test_succeeded_without_analyze_result_is_an_invalid_response(pdf: Path) -> None:
    client = make_client(max_retries=0)
    with (
        patch("httpx.Client.post", return_value=_submit_response()),
        patch("httpx.Client.get", return_value=_poll_response("succeeded")),
    ):
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_invalid_response"


def test_non_json_poll_body_is_an_invalid_response(pdf: Path) -> None:
    client = make_client(max_retries=0)
    bad = MagicMock()
    bad.status_code = 200
    bad.headers = {}
    bad.json.side_effect = ValueError("not json")

    with (
        patch("httpx.Client.post", return_value=_submit_response()),
        patch("httpx.Client.get", return_value=bad),
    ):
        with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
            client.analyze_document(pdf)

    assert exc_info.value.error_code == "azure_invalid_response"


def test_unreadable_source_file_fails_safely(tmp_path: Path) -> None:
    client = make_client(max_retries=0)
    with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
        client.analyze_document(tmp_path / "does-not-exist.pdf")

    assert exc_info.value.error_code == "azure_processing_failed"


def test_no_error_message_ever_contains_the_api_key(pdf: Path) -> None:
    """Every failure path must be safe to log and to surface internally."""
    client = make_client(max_retries=0)
    failures = [
        (_submit_response(status=401), None),
        (_submit_response(status=429), None),
        (_submit_response(operation=None), None),
    ]
    for submit, _ in failures:
        with patch("httpx.Client.post", return_value=submit):
            with pytest.raises(AzureDocumentIntelligenceError) as exc_info:
                client.analyze_document(pdf)
            rendered = f"{exc_info.value} {exc_info.value.error_code}"
            assert _API_KEY not in rendered
            assert "cognitiveservices.azure.com" not in rendered
