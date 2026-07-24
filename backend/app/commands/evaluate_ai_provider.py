"""evaluate_ai_provider — CLI for evaluating the configured AI provider.

Usage (from the backend directory):

    python -m app.commands.evaluate_ai_provider

or with a custom fixtures directory:

    python -m app.commands.evaluate_ai_provider \\
        --fixtures-dir ../../fixtures/ai/evaluation \\
        --verbose

Only fictional fixture data is used. No real applicant data is committed.
No paid AI services are called; the evaluation uses the configured provider
(mock by default).

Privacy:  evaluation fixture data is logged only at DEBUG level.
          Answer content is never printed in plain text to stdout in
          summary mode; only pass/fail metadata is shown.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import sys
from typing import Any

from app.ai.factory import build_provider

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

_DEFAULT_FIXTURES_DIR = (
    pathlib.Path(__file__).parents[3] / "fixtures" / "ai" / "evaluation"
)


def _load_fixtures(fixtures_dir: pathlib.Path) -> list[dict[str, Any]]:
    fixtures = []
    for path in sorted(fixtures_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_path"] = str(path)
            fixtures.append(data)
        except Exception as exc:
            logger.error("Failed to load fixture %s: %s", path, exc)
    return fixtures


def _check_normalized_value(expected: dict[str, Any], actual_value: object) -> bool:
    """Verify that all expected keys in the expected normalizedValue are present
    and equal in the actual value returned by the provider."""
    expected_nv = expected.get("normalizedValue")
    if expected_nv is None:
        return True  # No assertion required

    if isinstance(expected_nv, dict) and isinstance(actual_value, dict):
        for key, val in expected_nv.items():
            if actual_value.get(key) != val:
                return False
        return True

    # Scalar comparison (date, boolean, integer, …)
    return bool(actual_value == expected_nv)


async def run_evaluation(
    fixtures_dir: pathlib.Path,
    verbose: bool = False,
) -> tuple[int, int]:
    """Run all evaluation fixtures and return (passed, total)."""
    from app.ai.schemas import ExtractionRequest

    provider = build_provider()
    fixtures = _load_fixtures(fixtures_dir)

    if not fixtures:
        print(f"No fixtures found in {fixtures_dir}")
        return 0, 0

    passed = 0
    failed = 0
    errors = 0

    for fixture in fixtures:
        path_label = pathlib.Path(fixture["_path"]).name
        try:
            request = ExtractionRequest(
                fieldType=fixture["fieldType"],
                fieldConfig=fixture.get("fieldConfig", {}),
                answer=fixture["input"],
                userLanguage=fixture["userLanguage"],
                sourceLanguage=fixture["sourceLanguage"],
                outputLanguage=fixture["outputLanguage"],
            )
            result = await provider.extract_value(request)
            expected = fixture.get("expected", {})

            clarification_ok = result.requires_clarification == expected.get(
                "requiresClarification", False
            )
            nv_ok = _check_normalized_value(expected, result.normalized_value)

            if clarification_ok and nv_ok:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

            if verbose or status == "FAIL":
                desc = fixture.get("description", path_label)
                print(f"[{status}] {desc}")
                if status == "FAIL":
                    print(
                        f"       expected requiresClarification="
                        f"{expected.get('requiresClarification')} "
                        f"got={result.requires_clarification}"
                    )
                    print(
                        "       expected normalizedValue="
                        f"{expected.get('normalizedValue')} "
                        f"got={result.normalized_value}"
                    )
        except Exception as exc:
            errors += 1
            print(f"[ERROR] {path_label}: {exc}")

    total = passed + failed + errors
    print(f"\nResults: {passed}/{total} passed, {failed} failed, {errors} errors")
    return passed, total


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the configured AI provider against fictional fixtures."
    )
    parser.add_argument(
        "--fixtures-dir",
        type=pathlib.Path,
        default=_DEFAULT_FIXTURES_DIR,
        help="Directory containing JSON evaluation fixtures.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print all results, not just failures.",
    )
    args = parser.parse_args()

    passed, total = asyncio.run(run_evaluation(args.fixtures_dir, verbose=args.verbose))

    if total == 0 or passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
