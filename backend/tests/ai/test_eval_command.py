"""Tests for the evaluate_ai_provider CLI command."""

from __future__ import annotations

import asyncio
import pathlib

from app.commands.evaluate_ai_provider import run_evaluation

_FIXTURES_DIR = pathlib.Path(__file__).parents[3] / "fixtures" / "ai" / "evaluation"


def test_evaluation_fixtures_exist() -> None:
    assert _FIXTURES_DIR.exists(), f"Fixtures directory not found: {_FIXTURES_DIR}"
    fixtures = list(_FIXTURES_DIR.glob("*.json"))
    assert len(fixtures) >= 30, f"Expected >= 30 fixtures, found {len(fixtures)}"


def test_mock_provider_passes_all_fixtures() -> None:
    """MockAIProvider must pass 100% of the mock-compatible evaluation fixtures.

    Fixtures testing language-understanding (e.g. Arabic numerals → ISO date)
    are skipped under MockAIProvider.
    """
    passed, failed, skipped, errors = asyncio.run(
        run_evaluation(_FIXTURES_DIR, verbose=False)
    )
    assert passed >= 15
    assert failed == 0
    assert errors == 0


def test_evaluation_returns_zero_when_no_fixtures(
    tmp_path: pathlib.Path,
) -> None:
    passed, failed, skipped, errors = asyncio.run(
        run_evaluation(tmp_path, verbose=False)
    )
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert errors == 0
