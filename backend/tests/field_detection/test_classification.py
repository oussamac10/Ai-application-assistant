import pytest

from app.field_detection.classification import (
    acroform_widget_confidence,
    classify_label,
    classify_value_pattern,
)


@pytest.mark.parametrize(
    "label,expected_type",
    [
        ("Email", "email"),
        ("Email Address", "email"),
        ("Phone Number", "phone"),
        ("Mobile", "phone"),
        ("Date of Birth", "date"),
        ("Date", "date"),
        ("Home Address", "address"),
        ("Postal Code", "address"),
        ("Total Amount", "currency"),
        ("Price", "currency"),
        ("Quantity", "number"),
        ("Age", "number"),
        ("Comments", "multiline_text"),
        ("Additional Notes", "multiline_text"),
        ("Signature", "signature"),
        ("Full Name", "text"),
        ("", "text"),
    ],
)
def test_classify_label(label: str, expected_type: str) -> None:
    assert classify_label(label) == expected_type


@pytest.mark.parametrize(
    "value,expected_type",
    [
        ("john@example.com", "email"),
        ("42.50", "currency"),
        ("$42.50", "currency"),
        ("+1 555 123 4567", "phone"),
        ("not a recognizable value", None),
        ("", None),
    ],
)
def test_classify_value_pattern(value: str, expected_type: str | None) -> None:
    assert classify_value_pattern(value) == expected_type


def test_acroform_widget_confidence_higher_with_label() -> None:
    with_label = acroform_widget_confidence("checkbox", label_found=True)
    without_label = acroform_widget_confidence("checkbox", label_found=False)
    assert with_label > without_label


def test_acroform_widget_confidence_bounded() -> None:
    assert 0.0 <= acroform_widget_confidence("text", label_found=False) <= 1.0
    assert 0.0 <= acroform_widget_confidence("select", label_found=True) <= 1.0
