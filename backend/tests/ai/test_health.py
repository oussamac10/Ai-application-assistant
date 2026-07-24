"""Tests for GET /api/health/ai endpoint."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_ai_health_returns_ok_for_mock_provider(client: TestClient) -> None:
    """MockAIProvider.health_check always returns True → 200."""
    from app.ai.mock_provider import MockAIProvider

    with patch("app.api.health.get_provider", return_value=MockAIProvider()):
        response = client.get("/api/health/ai")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "provider" in body


def test_ai_health_returns_503_when_provider_unhealthy(
    client: TestClient,
) -> None:
    from app.ai.mock_provider import MockAIProvider

    unhealthy = MockAIProvider()

    async def _unhealthy() -> bool:
        return False

    unhealthy.health_check = _unhealthy  # type: ignore[method-assign]

    with patch("app.api.health.get_provider", return_value=unhealthy):
        response = client.get("/api/health/ai")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
