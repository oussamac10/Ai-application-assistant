"""Provider selection and configuration validation."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from app.ai.mock_provider import MockAIProvider
from app.core.config import Settings, settings
from app.translation.errors import TranslationConfigurationError
from app.translation.factory import (
    build_fallback_translation_provider,
    build_translation_provider,
)
from app.translation.providers.azure import AzureTranslatorProvider
from app.translation.providers.mock import MockTranslationProvider
from app.translation.providers.ollama import OllamaTranslationProvider


@pytest.fixture(autouse=True)
def restore_settings() -> Generator[None, None, None]:
    original = (
        settings.TRANSLATION_PROVIDER,
        settings.TRANSLATION_FALLBACK_PROVIDER,
        settings.AZURE_TRANSLATOR_ENABLED,
        settings.AZURE_TRANSLATOR_API_KEY,
    )
    yield
    (
        settings.TRANSLATION_PROVIDER,
        settings.TRANSLATION_FALLBACK_PROVIDER,
        settings.AZURE_TRANSLATOR_ENABLED,
        settings.AZURE_TRANSLATOR_API_KEY,
    ) = original


def test_builds_each_supported_provider() -> None:
    ai = MockAIProvider()
    assert isinstance(build_translation_provider("mock", ai), MockTranslationProvider)
    assert isinstance(
        build_translation_provider("ollama", ai), OllamaTranslationProvider
    )
    assert isinstance(build_translation_provider("azure", ai), AzureTranslatorProvider)


def test_provider_name_is_case_and_space_insensitive() -> None:
    provider = build_translation_provider("  AZURE ", MockAIProvider())
    assert provider.provider_name == "azure"


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(TranslationConfigurationError) as excinfo:
        build_translation_provider("deepl", MockAIProvider())
    assert "deepl" in str(excinfo.value)


def test_ollama_provider_requires_an_ai_provider() -> None:
    """It delegates to AIProvider's batch contract rather than reimplementing
    the prompt and repair logic, so it cannot be built without one."""
    with pytest.raises(TranslationConfigurationError):
        build_translation_provider("ollama", None)


@pytest.mark.parametrize("name", ["none", "None", "", "  ", "off", "null"])
def test_fallback_none_means_no_provider(name: str) -> None:
    assert build_fallback_translation_provider(name, MockAIProvider()) is None


def test_fallback_builds_a_real_provider_when_named() -> None:
    provider = build_fallback_translation_provider("ollama", MockAIProvider())
    assert isinstance(provider, OllamaTranslationProvider)


# ---------------------------------------------------------------------------
# Configuration validation — fail fast, but only when Azure is selected
# ---------------------------------------------------------------------------


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "TRANSLATION_PROVIDER": "ollama",
        "TRANSLATION_FALLBACK_PROVIDER": "none",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_azure_settings_are_not_required_when_azure_is_not_selected() -> None:
    """A developer with no Azure account must still be able to boot."""
    configured = _settings(
        AZURE_TRANSLATOR_API_KEY=None, AZURE_TRANSLATOR_ENABLED=False
    )
    assert configured.TRANSLATION_PROVIDER == "ollama"


def test_selecting_azure_without_enabling_it_fails_fast() -> None:
    with pytest.raises(ValueError, match="AZURE_TRANSLATOR_ENABLED"):
        _settings(TRANSLATION_PROVIDER="azure", AZURE_TRANSLATOR_ENABLED=False)


def test_selecting_azure_without_a_key_fails_fast() -> None:
    with pytest.raises(ValueError, match="AZURE_TRANSLATOR_API_KEY"):
        _settings(
            TRANSLATION_PROVIDER="azure",
            AZURE_TRANSLATOR_ENABLED=True,
            AZURE_TRANSLATOR_API_KEY=None,
        )


def test_selecting_azure_without_an_endpoint_fails_fast() -> None:
    with pytest.raises(ValueError, match="AZURE_TRANSLATOR_ENDPOINT"):
        _settings(
            TRANSLATION_PROVIDER="azure",
            AZURE_TRANSLATOR_ENABLED=True,
            AZURE_TRANSLATOR_API_KEY="k",
            AZURE_TRANSLATOR_ENDPOINT="  ",
        )


def test_azure_as_fallback_also_requires_configuration() -> None:
    """A fallback that cannot be built is not a fallback."""
    with pytest.raises(ValueError, match="AZURE_TRANSLATOR_ENABLED"):
        _settings(
            TRANSLATION_PROVIDER="ollama",
            TRANSLATION_FALLBACK_PROVIDER="azure",
            AZURE_TRANSLATOR_ENABLED=False,
        )


def test_unknown_provider_name_in_settings_fails_fast() -> None:
    with pytest.raises(ValueError, match="Unknown TRANSLATION_PROVIDER"):
        _settings(TRANSLATION_PROVIDER="deepl")


def test_fallback_equal_to_primary_is_rejected() -> None:
    """Falling back to the provider that just failed only doubles the latency
    of a failure."""
    with pytest.raises(ValueError, match="must differ"):
        _settings(TRANSLATION_PROVIDER="ollama", TRANSLATION_FALLBACK_PROVIDER="ollama")


def test_batch_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="AZURE_TRANSLATOR_MAX_BATCH_SIZE"):
        _settings(AZURE_TRANSLATOR_MAX_BATCH_SIZE=0)
