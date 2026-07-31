"""Drawing a captured signature into an exported PDF.

Two paths matter equally. A drawn signature must land inside the form's
signature box, unstretched. And "sign after printing" must leave that box
*exactly* as the form's author drew it — no placeholder, no stamp, no faint
line — because this is a document someone is about to hand to an authority.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.answers.signatures import PENDING_MANUAL_SIGNATURE
from app.pdf.signature_render import (
    SIGNATURE_INVALID,
    SignatureBox,
    SignatureRenderError,
    render_signature,
    should_render_signature,
)

_BOX = SignatureBox(page_number=1, x=100.0, y=600.0, width=200.0, height=60.0)

_SIGNATURE = {
    "strokes": [[[0.0, 0.0], [100.0, 50.0], [200.0, 10.0]]],
    "width": 400.0,
    "height": 100.0,
}


@pytest.fixture
def page():
    document = fitz.open()
    document.new_page(width=612, height=792)
    yield document[0]
    document.close()


def _drawn_points(page) -> list[tuple[float, float]]:
    """Every point the renderer actually put on the page."""
    points: list[tuple[float, float]] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            for element in item[1:]:
                if hasattr(element, "x") and hasattr(element, "y"):
                    points.append((element.x, element.y))
    return points


def test_a_signature_is_drawn_inside_its_box(page) -> None:
    render_signature(page, _BOX, _SIGNATURE)

    points = _drawn_points(page)
    assert points
    for x, y in points:
        assert _BOX.x <= x <= _BOX.x + _BOX.width
        assert _BOX.y <= y <= _BOX.y + _BOX.height


def test_the_aspect_ratio_is_preserved(page) -> None:
    """A stretched signature is not the one the person drew."""
    render_signature(page, _BOX, _SIGNATURE)

    points = _drawn_points(page)
    width = max(x for x, _ in points) - min(x for x, _ in points)
    height = max(y for _, y in points) - min(y for _, y in points)

    # Source strokes span 200 x 50, so the drawn shape must too, within
    # rounding.
    assert width / height == pytest.approx(200.0 / 50.0, rel=0.02)


def test_the_signature_is_centred_in_the_box(page) -> None:
    render_signature(page, _BOX, _SIGNATURE)

    points = _drawn_points(page)
    left_gap = min(x for x, _ in points) - _BOX.x
    right_gap = (_BOX.x + _BOX.width) - max(x for x, _ in points)

    assert left_gap == pytest.approx(right_gap, abs=1.0)


def test_a_tall_signature_still_fits(page) -> None:
    """The smaller ratio wins on both axes, so nothing escapes the box."""
    tall = {
        "strokes": [[[0.0, 0.0], [10.0, 400.0]]],
        "width": 20.0,
        "height": 400.0,
    }

    render_signature(page, _BOX, tall)

    for x, y in _drawn_points(page):
        assert _BOX.x <= x <= _BOX.x + _BOX.width
        assert _BOX.y <= y <= _BOX.y + _BOX.height


def test_every_stroke_is_drawn(page) -> None:
    three = {
        "strokes": [
            [[0.0, 0.0], [50.0, 20.0]],
            [[60.0, 0.0], [90.0, 30.0]],
            [[100.0, 5.0], [140.0, 25.0]],
        ],
        "width": 200.0,
        "height": 50.0,
    }

    assert render_signature(page, _BOX, three) == 3


def test_a_single_tap_is_not_lost(page) -> None:
    """A deliberate dot must still appear."""
    dot = {"strokes": [[[10.0, 10.0]]], "width": 100.0, "height": 100.0}

    render_signature(page, _BOX, dot)

    assert _drawn_points(page)


# ---------------------------------------------------------------------------
# Validation at export time
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"strokes": [[[float("nan"), 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [[[float("inf"), 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [[[9999.0, 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [], "width": 100.0, "height": 100.0},
        {"strokes": [[["x", "y"]]], "width": 100.0, "height": 100.0},
        "not a payload",
    ],
)
def test_malformed_payloads_are_rejected_at_export(page, payload) -> None:
    """Export reads from storage, and storage sits between capture and here.
    Revalidating is the cheapest place to catch a corrupted or tampered row
    before it becomes PDF drawing operators."""
    with pytest.raises(SignatureRenderError) as exc:
        render_signature(page, _BOX, payload)

    assert exc.value.error_code == SIGNATURE_INVALID


def test_an_export_error_never_carries_the_payload(page) -> None:
    with pytest.raises(SignatureRenderError) as exc:
        render_signature(
            page, _BOX, {"strokes": [[[8888.0, 7777.0]]], "width": 10.0, "height": 10.0}
        )

    message = str(exc.value)
    assert "8888" not in message
    assert "7777" not in message


# ---------------------------------------------------------------------------
# Sign after printing
# ---------------------------------------------------------------------------


def test_a_deferred_signature_puts_nothing_on_the_page() -> None:
    """The box is left exactly as the form's author drew it."""
    assert should_render_signature(PENDING_MANUAL_SIGNATURE) is False


def test_a_confirmed_signature_is_rendered() -> None:
    assert should_render_signature("confirmed") is True
    assert should_render_signature("awaiting_confirmation") is True


def test_an_unanswered_or_skipped_signature_is_not_rendered() -> None:
    assert should_render_signature(None) is False
    assert should_render_signature("skipped") is False
    assert should_render_signature("draft") is False


def test_the_manual_sign_path_leaves_the_page_untouched(page, tmp_path: Path) -> None:
    """End to end: a page exported for a deferred signature is byte-identical
    in its drawing content to one never touched."""
    before = len(page.get_drawings())

    if should_render_signature(PENDING_MANUAL_SIGNATURE):  # pragma: no cover
        render_signature(page, _BOX, _SIGNATURE)

    assert len(page.get_drawings()) == before


def test_rendering_creates_no_temporary_files(page, tmp_path: Path) -> None:
    """Vectors go straight onto the page — no PNG to write, cap, or delete, and
    no user-supplied image bytes to decode."""
    before = set(tmp_path.iterdir())

    render_signature(page, _BOX, _SIGNATURE)

    assert set(tmp_path.iterdir()) == before


def test_signature_rendering_logs_counts_only(
    page, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO"):
        render_signature(page, _BOX, _SIGNATURE)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "strokes=1" in logged
    assert "points=3" in logged
    # No coordinate reaches a log line.
    assert "100.0" not in logged
    assert "[[0.0, 0.0]" not in logged
