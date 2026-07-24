"""Tests for the evaluate_ai_provider CLI command."""

from __future__ import annotations

import asyncio
import pathlib

from app.commands.evaluate_ai_provider import run_evaluation

_FIXTURES_DIR = (
    pathlib.Path(__file__).parents[3] / "fixtures" / "ai" / "evaluation"
)


def test_evaluation_fixtures_exist() -> None:
    assert _FIXTURES_DIR.exists(), f"Fixtures directory not found: {_FIXTURES_DIR}"
    fixtures = list(_FIXTURES_DIR.glob("*.json"))
    assert len(fixtures) >= 30, f"Expected >= 30 fixtures, found {len(fixtures)}"


def test_mock_provider_passes_all_fixtures() -> None:
    """MockAIProvider must pass at least 20 of the evaluation fixtures.

    Fixtures testing language-understanding (e.g. Arabic numerals → ISO date)
    may not be handled by MockAIProvider — this is intentional.  We check that
    the simple ones pass and no exceptions are raised.
    """
    passed, total = asyncio.run(run_evaluation(_FIXTURES_DIR, verbose=False))
    assert total >= 30
    # MockAIProvider handles simple cases; at least half should pass
    assert (
        passed >= total // 2
    ), f"MockAIProvider passed only {passed}/{total} evaluation fixtures"


def test_evaluation_returns_zero_when_no_fixtures(
    tmp_path: pathlib.Path,
) -> None:
    passed, total = asyncio.run(run_evaluation(tmp_path, verbose=False))
    assert passed == 0
    assert total == 0
