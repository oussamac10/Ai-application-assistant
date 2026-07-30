"""Right-to-left layout handling, and the name collision that hid behind it.

The reported symptom was an Arabic form producing 2 questions from 27
candidates, one of them a single question whose label was three unrelated
fields ("family name / place of birth / postal code") run together.

There were two independent causes, and only one was geometric:

1. `normalize_field_name` stripped every non-ASCII character, so *every*
   Arabic label became the literal "field" and deduplication collapsed them.
2. Tokens were ordered and joined by ascending x, which reverses Arabic word
   order and puts a field's value area on the wrong side of its label.
"""

from __future__ import annotations

import pytest

from app.field_detection.direction import (
    is_rtl_language,
    join_tokens,
    value_side_is_left,
)
from app.field_detection.geometry import (
    group_tokens_into_lines,
    split_line_into_segments,
)
from app.field_detection.labeling import build_line_groups
from app.field_detection.normalization import (
    deduplicate_candidates,
    normalize_field_name,
)
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionToken,
)


def _token(text: str, x: float, y: float, width: float = 40, height: float = 12):
    return DetectionToken(
        text=text,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        source="native",
        confidence=1.0,
    )


# ---------------------------------------------------------------------------
# Name collision — the actual cause of 27 -> 2
# ---------------------------------------------------------------------------


ARABIC_LABELS = [
    "الاسم الأول",  # first name
    "اسم العائلة",  # family name
    "تاريخ الميلاد",  # date of birth
    "مكان الميلاد",  # place of birth
    "العنوان الكامل",  # full address
    "المدينة",  # city
    "الرمز البريدي",  # postal code
    "رقم الهاتف",  # phone number
    "البريد الإلكتروني",  # email
]


def test_arabic_labels_produce_distinct_normalized_names() -> None:
    names = [normalize_field_name(label) for label in ARABIC_LABELS]
    assert len(set(names)) == len(
        ARABIC_LABELS
    ), f"Arabic labels collided: {sorted(set(names))}"
    assert "field" not in names


def test_family_name_place_of_birth_and_postal_code_stay_separate() -> None:
    """The three labels that were merged into one question."""
    names = {
        normalize_field_name("اسم العائلة"),
        normalize_field_name("مكان الميلاد"),
        normalize_field_name("الرمز البريدي"),
    }
    assert len(names) == 3


def test_arabic_candidates_are_not_deduplicated_into_one() -> None:
    candidates = [
        DetectedFieldCandidate(
            candidate_key=f"c{index}",
            page_number=1,
            label=label,
            normalized_name=normalize_field_name(label),
            field_type="text",
            confidence=0.8,
            source="native",
        )
        for index, label in enumerate(ARABIC_LABELS)
    ]

    assert len(deduplicate_candidates(candidates)) == len(ARABIC_LABELS)


def test_latin_normalization_is_unchanged() -> None:
    """German and English keys must be byte-identical to before."""
    assert normalize_field_name("Vermieter Straße Nr") == "vermieter_stra_e_nr"
    assert normalize_field_name("Full Name") == "full_name"
    assert normalize_field_name("E-Mail Address!") == "e_mail_address"
    assert normalize_field_name("PLZ, Ort") == "plz_ort"
    assert normalize_field_name("   ") == "field"


def test_punctuation_only_labels_stay_distinct() -> None:
    assert normalize_field_name("...") != normalize_field_name("---")


# ---------------------------------------------------------------------------
# Direction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("language", ["ar", "he", "fa", "ur", "ar-EG", "AR"])
def test_rtl_languages_are_recognized(language: str) -> None:
    assert is_rtl_language(language) is True


@pytest.mark.parametrize("language", ["de", "en", "fr", None, "", "und"])
def test_ltr_languages_are_not_rtl(language: str | None) -> None:
    assert is_rtl_language(language) is False


def test_rtl_join_preserves_arabic_word_order() -> None:
    """Joining by ascending x reverses an Arabic sentence: the form's title
    came back as `سكني دعم طلب نموذج` instead of `نموذج طلب دعم سكني`."""
    tokens = [
        _token("سكني", x=100, y=50),
        _token("دعم", x=150, y=50),
        _token("طلب", x=200, y=50),
        _token("نموذج", x=250, y=50),
    ]

    assert join_tokens(tokens, rtl=True) == "نموذج طلب دعم سكني"
    assert join_tokens(tokens, rtl=False) == "سكني دعم طلب نموذج"


def test_join_never_alters_the_characters_themselves() -> None:
    """Order is direction-aware; the strings are not touched, so Arabic
    characters and combining marks survive byte for byte."""
    original = "الاسم الكامل"
    tokens = [_token(original, x=100, y=50)]

    assert join_tokens(tokens, rtl=True) == original
    assert join_tokens(tokens, rtl=False) == original


def test_ltr_join_is_unchanged() -> None:
    tokens = [_token("Vermieter", x=100, y=50), _token("Name", x=160, y=50)]
    assert join_tokens(tokens, rtl=False) == "Vermieter Name"


def test_value_area_is_on_the_left_for_rtl() -> None:
    assert value_side_is_left(rtl=True) is True
    assert value_side_is_left(rtl=False) is False


# ---------------------------------------------------------------------------
# Line and segment ordering
# ---------------------------------------------------------------------------


def test_rtl_lines_are_ordered_right_to_left() -> None:
    tokens = (
        _token("يسار", x=100, y=50),
        _token("وسط", x=200, y=50),
        _token("يمين", x=300, y=50),
    )
    line = group_tokens_into_lines(tokens, rtl=True)[0]

    assert [t.text for t in line] == ["يمين", "وسط", "يسار"]


def test_ltr_lines_are_still_ordered_left_to_right() -> None:
    tokens = (
        _token("left", x=100, y=50),
        _token("middle", x=200, y=50),
        _token("right", x=300, y=50),
    )
    line = group_tokens_into_lines(tokens, rtl=False)[0]

    assert [t.text for t in line] == ["left", "middle", "right"]


def test_two_labels_on_one_rtl_row_stay_separate_segments() -> None:
    """The row `الاسم الأول | اسم العائلة` is two fields, not one. A wide gap
    separates them, and each must remain its own segment."""
    tokens = [
        _token("العائلة", x=100, y=50),
        _token("اسم", x=145, y=50),
        _token("الأول", x=400, y=50),
        _token("الاسم", x=445, y=50),
    ]
    segments = split_line_into_segments(tokens, rtl=True)

    assert len(segments) == 2, "unrelated labels on one row were merged"
    # Reading order: the rightmost segment comes first.
    assert join_tokens(segments[0], rtl=True) == "الاسم الأول"
    assert join_tokens(segments[1], rtl=True) == "اسم العائلة"


def test_rtl_line_groups_keep_each_label_distinct() -> None:
    tokens = (
        _token("العائلة", x=100, y=50),
        _token("اسم", x=145, y=50),
        _token("الأول", x=400, y=50),
        _token("الاسم", x=445, y=50),
    )
    groups = build_line_groups(1, tokens, rtl=True)

    assert len(groups) == 1
    texts = [phrase.text for phrase in groups[0]]
    assert texts == ["الاسم الأول", "اسم العائلة"]
    assert len({normalize_field_name(t) for t in texts}) == 2


def test_ltr_line_groups_are_unchanged() -> None:
    tokens = (
        _token("Signature:", x=100, y=50),
        _token("Date:", x=400, y=50),
    )
    groups = build_line_groups(1, tokens, rtl=False)

    assert [phrase.text for phrase in groups[0]] == ["Signature", "Date"]
