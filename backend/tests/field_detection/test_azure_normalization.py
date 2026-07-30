"""Unit tests for Azure Document Intelligence coordinate conversion and
candidate normalization. No HTTP and no Azure SDK is involved."""

from __future__ import annotations

from typing import Any

import pytest

from app.field_detection.azure_normalization import (
    build_detection_pages,
    build_page_geometries,
    build_page_geometry,
    extract_key_value_candidates,
    merge_bounding_regions,
    polygon_to_bounding_box,
)


def _inch_page(**overrides: Any) -> dict[str, Any]:
    page = {"pageNumber": 1, "unit": "inch", "width": 8.5, "height": 11.0}
    page.update(overrides)
    return page


# ---------------------------------------------------------------------------
# Page geometry / unit conversion
# ---------------------------------------------------------------------------


def test_inch_page_scales_by_72_points_per_inch() -> None:
    geometry = build_page_geometry(_inch_page())
    assert geometry is not None
    assert geometry.scale_x == 72.0
    assert geometry.scale_y == 72.0
    assert geometry.width_points == pytest.approx(612.0)
    assert geometry.height_points == pytest.approx(792.0)


def test_pixel_page_scales_to_the_real_pdf_page_size() -> None:
    # 1700x2200 px rendered from a US-Letter (612x792pt) page.
    geometry = build_page_geometry(
        _inch_page(unit="pixel", width=1700, height=2200), (612.0, 792.0)
    )
    assert geometry is not None
    assert geometry.scale_x == pytest.approx(612.0 / 1700.0)
    assert geometry.width_points == pytest.approx(612.0)
    assert geometry.height_points == pytest.approx(792.0)


def test_pixel_page_without_pdf_size_falls_back_to_96_dpi() -> None:
    geometry = build_page_geometry(_inch_page(unit="pixel", width=816, height=1056))
    assert geometry is not None
    assert geometry.scale_x == pytest.approx(72.0 / 96.0)
    assert geometry.width_points == pytest.approx(612.0)


def test_page_with_missing_or_invalid_size_is_rejected() -> None:
    assert build_page_geometry(_inch_page(width=0)) is None
    assert build_page_geometry(_inch_page(height=-1)) is None
    assert build_page_geometry(_inch_page(pageNumber=0)) is None
    assert build_page_geometry({"pageNumber": "x", "width": "y", "height": "z"}) is None


# ---------------------------------------------------------------------------
# Polygon -> BoundingBox
# ---------------------------------------------------------------------------


def test_polygon_converts_to_point_space_bounding_box() -> None:
    geometry = build_page_geometry(_inch_page())
    # A 1x0.5 inch box at (1, 2) inches.
    box = polygon_to_bounding_box([1.0, 2.0, 2.0, 2.0, 2.0, 2.5, 1.0, 2.5], geometry)
    assert box is not None
    assert box.x == pytest.approx(72.0)
    assert box.y == pytest.approx(144.0)
    assert box.width == pytest.approx(72.0)
    assert box.height == pytest.approx(36.0)


def test_rotated_polygon_becomes_its_axis_aligned_bounds() -> None:
    """A skewed polygon (Azure reports content rotation as a rotated
    quad) still yields a usable axis-aligned box."""
    geometry = build_page_geometry(_inch_page())
    box = polygon_to_bounding_box([1.0, 2.0, 2.0, 2.1, 1.9, 2.6, 0.9, 2.5], geometry)
    assert box is not None
    assert box.x == pytest.approx(0.9 * 72.0)
    assert box.y == pytest.approx(2.0 * 72.0)
    assert box.width == pytest.approx((2.0 - 0.9) * 72.0)


def test_normalized_polygon_is_scaled_by_page_size() -> None:
    geometry = build_page_geometry(_inch_page())
    # All coordinates within 0-1 => normalized, so 0.5 means half a page.
    box = polygon_to_bounding_box([0.0, 0.0, 0.5, 0.0, 0.5, 0.5, 0.0, 0.5], geometry)
    assert box is not None
    assert box.width == pytest.approx(0.5 * 8.5 * 72.0)
    assert box.height == pytest.approx(0.5 * 11.0 * 72.0)


def test_missing_or_malformed_polygon_returns_none_rather_than_guessing() -> None:
    geometry = build_page_geometry(_inch_page())
    assert polygon_to_bounding_box(None, geometry) is None
    assert polygon_to_bounding_box([], geometry) is None
    assert polygon_to_bounding_box([1.0, 2.0], geometry) is None  # too few points
    assert polygon_to_bounding_box([1.0, 2.0, 3.0], geometry) is None  # odd count
    assert polygon_to_bounding_box(["a", "b", "c", "d"], geometry) is None
    # Degenerate (zero-area) polygons are rejected.
    assert (
        polygon_to_bounding_box([2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0], geometry)
        is None
    )


def test_polygon_without_geometry_returns_none() -> None:
    assert (
        polygon_to_bounding_box([1.0, 2.0, 2.0, 2.0, 2.0, 3.0, 1.0, 3.0], None) is None
    )


# ---------------------------------------------------------------------------
# boundingRegions
# ---------------------------------------------------------------------------


def test_multiple_regions_on_one_page_are_merged_into_their_union() -> None:
    geometries = {1: build_page_geometry(_inch_page())}
    page, box = merge_bounding_regions(
        [
            {"pageNumber": 1, "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 2.0, 1.0, 2.0]},
            {"pageNumber": 1, "polygon": [3.0, 1.0, 4.0, 1.0, 4.0, 2.0, 3.0, 2.0]},
        ],
        geometries,  # type: ignore[arg-type]
    )
    assert page == 1
    assert box is not None
    assert box.x == pytest.approx(72.0)
    assert box.width == pytest.approx(3.0 * 72.0)


def test_regions_spanning_pages_keep_the_first_page_only() -> None:
    geometries = {
        1: build_page_geometry(_inch_page()),
        2: build_page_geometry(_inch_page(pageNumber=2)),
    }
    page, box = merge_bounding_regions(
        [
            {"pageNumber": 1, "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 2.0, 1.0, 2.0]},
            {"pageNumber": 2, "polygon": [1.0, 1.0, 8.0, 1.0, 8.0, 2.0, 1.0, 2.0]},
        ],
        geometries,  # type: ignore[arg-type]
    )
    assert page == 1
    assert box is not None
    assert box.width == pytest.approx(72.0)


def test_empty_or_malformed_regions_are_safe() -> None:
    assert merge_bounding_regions(None, {}) == (None, None)
    assert merge_bounding_regions([], {}) == (None, None)
    assert merge_bounding_regions(["not-a-dict"], {}) == (None, None)  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# words / selection marks -> DetectionPageInput
# ---------------------------------------------------------------------------


def test_words_become_detection_tokens_in_point_space() -> None:
    analyze_result = {
        "pages": [
            _inch_page(
                words=[
                    {
                        "content": "IBAN",
                        "polygon": [1.0, 1.0, 1.5, 1.0, 1.5, 1.2, 1.0, 1.2],
                        "confidence": 0.97,
                    }
                ]
            )
        ]
    }
    geometries = build_page_geometries(analyze_result)
    pages = build_detection_pages(analyze_result, geometries)

    assert len(pages) == 1
    assert len(pages[0].tokens) == 1
    token = pages[0].tokens[0]
    assert token.text == "IBAN"
    assert token.confidence == pytest.approx(0.97)
    assert token.bounding_box.x == pytest.approx(72.0)


def test_selection_marks_become_checkbox_marker_tokens() -> None:
    """A selection mark is emitted as the same "[_]" glyph the local
    provider's choice-group detection already understands."""
    analyze_result = {
        "pages": [
            _inch_page(
                words=[],
                selectionMarks=[
                    {
                        "state": "selected",
                        "polygon": [1.0, 1.0, 1.1, 1.0, 1.1, 1.1, 1.0, 1.1],
                        "confidence": 0.9,
                    }
                ],
            )
        ]
    }
    pages = build_detection_pages(analyze_result, build_page_geometries(analyze_result))
    assert [t.text for t in pages[0].tokens] == ["[_]"]


def test_one_malformed_word_does_not_discard_the_page() -> None:
    analyze_result = {
        "pages": [
            _inch_page(
                words=[
                    {
                        "content": "Good",
                        "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 1.2, 1.0, 1.2],
                    },
                    {"content": "NoPolygon"},
                    {
                        "content": "",
                        "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 1.2, 1.0, 1.2],
                    },
                    "not-a-dict",
                ]
            )
        ]
    }
    pages = build_detection_pages(analyze_result, build_page_geometries(analyze_result))
    assert [t.text for t in pages[0].tokens] == ["Good"]


def test_word_without_confidence_gets_a_sane_default_not_zero() -> None:
    analyze_result = {
        "pages": [
            _inch_page(
                words=[
                    {
                        "content": "X",
                        "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 1.2, 1.0, 1.2],
                    }
                ]
            )
        ]
    }
    pages = build_detection_pages(analyze_result, build_page_geometries(analyze_result))
    confidence = pages[0].tokens[0].confidence
    assert 0.0 < confidence < 1.0


# ---------------------------------------------------------------------------
# keyValuePairs
# ---------------------------------------------------------------------------


def _kv(key: str, value: str | None = None, confidence: float = 0.9) -> dict[str, Any]:
    poly = [1.0, 1.0, 2.0, 1.0, 2.0, 1.2, 1.0, 1.2]
    pair: dict[str, Any] = {
        "key": {
            "content": key,
            "boundingRegions": [{"pageNumber": 1, "polygon": poly}],
        },
        "confidence": confidence,
    }
    if value is not None:
        pair["value"] = {
            "content": value,
            "boundingRegions": [{"pageNumber": 1, "polygon": poly}],
        }
    return pair


def test_key_value_pair_becomes_a_candidate_with_both_boxes() -> None:
    geometries = build_page_geometries({"pages": [_inch_page()]})
    candidates = extract_key_value_candidates(
        {"keyValuePairs": [_kv("IBAN:", "DE02120300000000202051")]}, geometries
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.label == "IBAN"
    assert candidate.normalized_name == "iban"
    assert candidate.page_number == 1
    assert candidate.label_bounding_box is not None
    assert candidate.input_bounding_box is not None
    assert candidate.existing_value == "DE02120300000000202051"


def test_key_value_blank_run_value_is_never_kept_as_a_prefilled_answer() -> None:
    geometries = build_page_geometries({"pages": [_inch_page()]})
    candidates = extract_key_value_candidates(
        {"keyValuePairs": [_kv("Name:", "…………………………")]}, geometries
    )
    assert len(candidates) == 1
    assert candidates[0].existing_value is None


def test_key_value_headings_and_prose_are_not_turned_into_fields() -> None:
    geometries = build_page_geometries({"pages": [_inch_page()]})
    candidates = extract_key_value_candidates(
        {
            "keyValuePairs": [
                _kv("§ 4 Mietkosten"),
                _kv(
                    "Zwischen den Parteien gelten zusätzlich folgende Regelungen "
                    "als bindend"
                ),
                _kv("…………………………"),
                _kv(""),
            ]
        },
        geometries,
    )
    assert candidates == []


def test_one_malformed_key_value_pair_does_not_fail_the_others() -> None:
    geometries = build_page_geometries({"pages": [_inch_page()]})
    candidates = extract_key_value_candidates(
        {
            "keyValuePairs": [
                "not-a-dict",
                {"key": "not-a-dict-either"},
                {"key": {"content": "Bank:"}},  # no boundingRegions -> no page
                _kv("BIC:", "MARKDEF1100"),
            ]
        },
        geometries,
    )
    assert [c.label for c in candidates] == ["BIC"]


def test_key_value_confidence_is_clamped_into_the_expected_band() -> None:
    geometries = build_page_geometries({"pages": [_inch_page()]})
    low = extract_key_value_candidates(
        {"keyValuePairs": [_kv("Name:", "x", confidence=0.01)]}, geometries
    )[0]
    high = extract_key_value_candidates(
        {"keyValuePairs": [_kv("Name:", "x", confidence=1.0)]}, geometries
    )[0]
    # Azure's own confidence informs but never dictates: a pairing is
    # never treated as certain, nor as unusable.
    assert 0.6 <= low.confidence <= 0.9
    assert 0.6 <= high.confidence <= 0.9
