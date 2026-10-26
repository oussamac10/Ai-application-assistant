"""Test-suite-wide safety net for provider selection.

`Settings` reads the developer's real `.env`, so whatever provider is
configured for local manual testing becomes the default inside the test
process too. With `TRANSLATION_PROVIDER=azure` that made the suite issue live
Azure Translator calls: every test that builds a service without injecting a
provider hit the network, spent the full 30 s timeout plus a retry, and the run
hung for minutes instead of finishing in about one.

`docs/claude/domain-rules.md` is unambiguous that automated tests must never
call a live or paid provider, so the defaults are pinned here rather than left
to whatever happens to be in `.env`. A test that wants a specific provider
still injects one explicitly — which every provider test already does — so this
only changes the *ambient* default.

Field detection is pinned for the same reason: `FIELD_DETECTION_PROVIDER=azure`
in a developer's `.env` would otherwise send fixture PDFs to Azure Document
Intelligence during an ordinary test run.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True, scope="session")
def _never_call_live_providers() -> Generator[None, None, None]:
    original = (
        settings.TRANSLATION_PROVIDER,
        settings.TRANSLATION_FALLBACK_PROVIDER,
        settings.AZURE_TRANSLATOR_ENABLED,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
        settings.FIELD_DETECTION_PROVIDER,
        settings.OCR_PROVIDER,
        settings.AI_PROVIDER,
        settings.JOB_EXECUTION_MODE,
        settings.RATE_LIMIT_ENABLED,
        settings.REDIS_URL,
        settings.EMAIL_PROVIDER,
    )

    settings.TRANSLATION_PROVIDER = "mock"
    settings.TRANSLATION_FALLBACK_PROVIDER = "none"
    settings.AZURE_TRANSLATOR_ENABLED = False
    settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED = False
    if settings.FIELD_DETECTION_PROVIDER in ("azure", "hybrid"):
        settings.FIELD_DETECTION_PROVIDER = "local"
    settings.OCR_PROVIDER = "mock"
    if settings.AI_PROVIDER != "mock":
        settings.AI_PROVIDER = "mock"
    settings.JOB_EXECUTION_MODE = "inline"
    settings.RATE_LIMIT_ENABLED = False
    settings.REDIS_URL = None
    settings.EMAIL_PROVIDER = "mock"

    yield

    (
        settings.TRANSLATION_PROVIDER,
        settings.TRANSLATION_FALLBACK_PROVIDER,
        settings.AZURE_TRANSLATOR_ENABLED,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
        settings.FIELD_DETECTION_PROVIDER,
        settings.OCR_PROVIDER,
        settings.AI_PROVIDER,
        settings.JOB_EXECUTION_MODE,
        settings.RATE_LIMIT_ENABLED,
        settings.REDIS_URL,
        settings.EMAIL_PROVIDER,
    ) = original
