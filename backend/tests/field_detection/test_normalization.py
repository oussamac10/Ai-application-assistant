from app.field_detection.normalization import (
    deduplicate_candidates,
    downgrade_low_confidence,
    normalize_field_name,
    sort_candidates_deterministically,
)
from app.field_detection.providers.base import BoundingBox, DetectedFieldCandidate


def _candidate(
    key: str,
    page: int = 1,
    field_type: str = "text",
    confidence: float = 0.9,
    normalized_name: str = "field",
    box: BoundingBox | None = None,
) -> DetectedFieldCandidate:
    return DetectedFieldCandidate(
        candidate_key=key,
        page_number=page,
        label="Label",
        normalized_name=normalized_name,
        field_type=field_type,
        confidence=confidence,
        source="native",
        input_bounding_box=box,
    )


def test_normalize_field_name_slugifies() -> None:
    assert normalize_field_name("Full Name") == "full_name"
    assert normalize_field_name("E-Mail Address!") == "e_mail_address"
    assert normalize_field_name("   ") == "field"
    assert (
        normalize_field_name("Date of Birth (DD/MM/YYYY)") == "date_of_birth_dd_mm_yyyy"
    )


def test_downgrade_low_confidence_forces_unknown() -> None:
    low = _candidate("k1", field_type="email", confidence=0.2)
    result = downgrade_low_confidence(low)
    assert result.field_type == "unknown"
    assert result.confidence == 0.2


def test_downgrade_low_confidence_leaves_high_confidence_alone() -> None:
    high = _candidate("k1", field_type="email", confidence=0.9)
    result = downgrade_low_confidence(high)
    assert result.field_type == "email"


def test_downgrade_low_confidence_is_noop_for_already_unknown() -> None:
    already_unknown = _candidate("k1", field_type="unknown", confidence=0.1)
    result = downgrade_low_confidence(already_unknown)
    assert result is already_unknown


def test_deduplicate_candidates_keeps_first_per_normalized_name() -> None:
    first = _candidate("k1", normalized_name="email")
    duplicate = _candidate("k2", normalized_name="email")
    other = _candidate("k3", normalized_name="phone")

    result = deduplicate_candidates([first, duplicate, other])

    assert result == [first, other]


def test_sort_candidates_deterministically_orders_by_page_then_position() -> None:
    c_page2 = _candidate("a", page=2, box=BoundingBox(x=0, y=0, width=10, height=10))
    c_page1_bottom = _candidate(
        "b", page=1, box=BoundingBox(x=0, y=300, width=10, height=10)
    )
    c_page1_top = _candidate(
        "c", page=1, box=BoundingBox(x=0, y=100, width=10, height=10)
    )

    result = sort_candidates_deterministically([c_page2, c_page1_bottom, c_page1_top])

    assert [c.candidate_key for c in result] == ["c", "b", "a"]


def test_sort_candidates_deterministically_stable_for_missing_boxes() -> None:
    no_box_a = _candidate("a", box=None)
    no_box_b = _candidate("b", box=None)

    result = sort_candidates_deterministically([no_box_b, no_box_a])

    assert [c.candidate_key for c in result] == ["a", "b"]
