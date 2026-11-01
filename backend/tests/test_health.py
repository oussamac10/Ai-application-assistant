from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_success() -> None:
    # Mock engine.connect to succeed (return a mock connection that can execute a query)
    mock_conn = MagicMock()
    with patch("app.api.health.engine.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn

        response = client.get("/api/health/database")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "connected"}
        mock_connect.assert_called_once()


def test_database_health_failure() -> None:
    # Mock engine.connect to raise an exception
    with patch("app.api.health.engine.connect") as mock_connect:
        mock_connect.side_effect = Exception("Database connection failed")

        response = client.get("/api/health/database")
        assert response.status_code == 503
        assert response.json() == {"status": "error", "database": "unavailable"}
        mock_connect.assert_called_once()


def test_ai_health_returns_ok_for_mock_provider() -> None:
    from app.ai.mock_provider import MockAIProvider

    with patch("app.api.health.get_provider", return_value=MockAIProvider()):
        response = client.get("/api/health/ai")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "provider" in body


def test_ai_health_returns_503_when_provider_unhealthy() -> None:
    from app.ai.mock_provider import MockAIProvider

    unhealthy = MockAIProvider()

    async def _unhealthy() -> bool:
        return False

    unhealthy.health_check = _unhealthy  # type: ignore[method-assign]

    with patch("app.api.health.get_provider", return_value=unhealthy):
        response = client.get("/api/health/ai")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
