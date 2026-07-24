"""Tests for AIProviderFactory — no module reloads, proper monkeypatching."""

from __future__ import annotations

import pytest

import app.ai.factory as _factory_mod
from app.ai.errors import AIProviderConfigurationError
from app.ai.factory import build_provider
from app.ai.mock_provider import AIProvider, MockAIProvider
from app.ai.ollama_provider import OllamaAIProvider
from app.core.config import settings


@pytest.fixture(autouse=True)
def _reset_provider_singleton() -> pytest.FixtureFunction:  # type: ignore[type-arg]
    """Reset the process-level AI provider singleton before and after each test."""
    original = _factory_mod._provider
    _factory_mod._provider = None
    yield
    _factory_mod._provider = original


def test_build_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    provider = build_provider()
    assert isinstance(provider, MockAIProvider)


def test_build_ollama_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "test-model")
    provider = build_provider()
    assert isinstance(provider, OllamaAIProvider)


def test_unknown_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown provider name must raise AIProviderConfigurationError."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "nonexistent")
    with pytest.raises(AIProviderConfigurationError):
        build_provider()


def test_mock_provider_satisfies_protocol() -> None:
    provider = MockAIProvider()
    assert isinstance(provider, AIProvider)
