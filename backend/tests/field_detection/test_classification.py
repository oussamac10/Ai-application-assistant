import pytest

from app.field_detection.classification import (
    acroform_widget_confidence,
    choice_group_confidence,
    classify_label,
    classify_value_pattern,
    is_confirmation_sentence,
    is_footer_metadata,
    marker_type,
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


@pytest.mark.parametrize(
    "text,expected_kind",
    [
        ("[_]", "checkbox"),
        ("[ ]", "checkbox"),
        ("[x]", "checkbox"),
        ("(_)", "radio"),
        ("( )", "radio"),
        ("(x)", "radio"),
        ("Housing", None),
        ("[Housing]", None),
    ],
)
def test_marker_type(text: str, expected_kind: str | None) -> None:
    assert marker_type(text) == expected_kind


@pytest.mark.parametrize(
    "text,expected",
    [
        ("I confirm that the information above is accurate.", True),
        ("I agree to the terms.", True),
        ("I certify this is correct.", True),
        ("Housing", False),
        ("", False),
    ],
)
def test_is_confirmation_sentence(text: str, expected: bool) -> None:
    assert is_confirmation_sentence(text) == expected


def test_is_footer_metadata_requires_both_keyword_and_footer_position() -> None:
    assert is_footer_metadata("Test document ID: TD-1", top_y=750, page_height=792)
    # same keyword, but not in the footer region
    assert not is_footer_metadata("Test document ID: TD-1", top_y=100, page_height=792)
    # in the footer region, but no metadata keyword — a legitimate field
    assert not is_footer_metadata("Signature", top_y=750, page_height=792)


def test_choice_group_confidence_prefers_marker_evidence() -> None:
    assert choice_group_confidence("checkbox") > choice_group_confidence(None)
    assert choice_group_confidence("radio") > choice_group_confidence(None)
