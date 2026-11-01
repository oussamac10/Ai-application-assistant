"""Tests for Azure table cell extraction, selection mark typing, and label sanitization."""

from app.field_detection.azure_normalization import (
    AzurePageGeometry,
    _split_key_lines,
    extract_key_value_candidates,
    extract_table_candidates,
)


def _sample_geometry() -> dict[int, AzurePageGeometry]:
    return {
        1: AzurePageGeometry(
            page_number=1,
            width=8.5,
            height=11.0,
            unit="inch",
            scale_x=72.0,
            scale_y=72.0,
        )
    }


def test_azure_selection_marks_classified_as_checkbox():
    """Key-value pairs with :unselected: or :selected: must be typed as checkbox."""
    analyze_result = {
        "keyValuePairs": [
            {
                "key": {
                    "content": "Erteilung",
                    "boundingRegions": [
                        {
                            "pageNumber": 1,
                            "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 1.2, 1.0, 1.2],
                        }
                    ],
                },
                "value": {
                    "content": ":unselected:",
                    "boundingRegions": [
                        {
                            "pageNumber": 1,
                            "polygon": [0.8, 1.0, 1.0, 1.0, 1.0, 1.2, 0.8, 1.2],
                        }
                    ],
                },
                "confidence": 0.95,
            },
            {
                "key": {
                    "content": "männlich",
                    "boundingRegions": [
                        {
                            "pageNumber": 1,
                            "polygon": [1.0, 2.0, 2.0, 2.0, 2.0, 2.2, 1.0, 2.2],
                        }
                    ],
                },
                "value": {
                    "content": ":selected:",
                    "boundingRegions": [
                        {
                            "pageNumber": 1,
                            "polygon": [0.8, 2.0, 1.0, 2.0, 1.0, 2.2, 0.8, 2.2],
                        }
                    ],
                },
                "confidence": 0.95,
            },
        ]
    }
    candidates = extract_key_value_candidates(analyze_result, _sample_geometry())
    assert len(candidates) == 2
    assert candidates[0].field_type == "checkbox"
    assert candidates[0].existing_value is None  # unselected

    assert candidates[1].field_type == "checkbox"
    assert candidates[1].existing_value == "true"  # selected


def test_split_key_lines_filters_degenerate_fragments():
    """Punctuation, language codes, and short prepositions must not become candidate lines."""
    raw_label = (
        "Name at birth / Nom de naissance / Kızlık\n"
        "/\n"
        "(dans\n"
        "en\n"
        "und\n"
        "Geburtsort"
    )
    lines = _split_key_lines(raw_label)
    assert "/" not in lines
    assert "(dans" not in lines
    assert "en" not in lines
    assert "und" not in lines
    assert any("Name at birth" in line for line in lines)
    assert any("Geburtsort" in line for line in lines)


def test_extract_table_candidates_detects_label_and_input_cell():
    """Table cells with a label and an adjacent empty input box become candidates."""
    analyze_result = {
        "tables": [
            {
                "rowCount": 2,
                "columnCount": 2,
                "cells": [
                    {
                        "rowIndex": 0,
                        "columnIndex": 0,
                        "content": "2. Familienname",
                        "boundingRegions": [
                            {
                                "pageNumber": 1,
                                "polygon": [1.0, 1.0, 3.0, 1.0, 3.0, 1.5, 1.0, 1.5],
                            }
                        ],
                    },
                    {
                        "rowIndex": 0,
                        "columnIndex": 1,
                        "content": "",  # Empty input blank
                        "boundingRegions": [
                            {
                                "pageNumber": 1,
                                "polygon": [3.0, 1.0, 6.0, 1.0, 6.0, 1.5, 3.0, 1.5],
                            }
                        ],
                    },
                    {
                        "rowIndex": 1,
                        "columnIndex": 0,
                        "content": "4. Geburtsdatum",
                        "boundingRegions": [
                            {
                                "pageNumber": 1,
                                "polygon": [1.0, 2.0, 3.0, 2.0, 3.0, 2.5, 1.0, 2.5],
                            }
                        ],
                    },
                    {
                        "rowIndex": 1,
                        "columnIndex": 1,
                        "content": "",
                        "boundingRegions": [
                            {
                                "pageNumber": 1,
                                "polygon": [3.0, 2.0, 6.0, 2.0, 6.0, 2.5, 3.0, 2.5],
                            }
                        ],
                    },
                ],
            }
        ]
    }
    candidates = extract_table_candidates(analyze_result, _sample_geometry())
    assert len(candidates) == 2
    assert candidates[0].label == "2. Familienname"
    assert candidates[0].field_type in ("text", "string")
    assert candidates[1].label == "4. Geburtsdatum"
    assert candidates[1].field_type == "date"
    assert candidates[0].input_bounding_box is not None
