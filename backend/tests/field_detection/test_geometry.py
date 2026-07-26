from app.field_detection.geometry import (
    group_tokens_into_lines,
    is_above,
    is_left_of,
    union_bounding_box,
)
from app.field_detection.providers.base import BoundingBox, DetectionToken


def _token(
    text: str, x: float, y: float, width: float = 40, height: float = 20
) -> DetectionToken:
    return DetectionToken(
        text=text,
        confidence=1.0,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        source="native",
    )


def test_is_left_of_true_for_same_line_adjacent_box() -> None:
    label = BoundingBox(x=100, y=200, width=80, height=20)
    target = BoundingBox(x=190, y=202, width=200, height=20)
    assert is_left_of(label, target, max_gap=40) is True


def test_is_left_of_false_when_gap_too_large() -> None:
    label = BoundingBox(x=100, y=200, width=80, height=20)
    target = BoundingBox(x=400, y=202, width=200, height=20)
    assert is_left_of(label, target, max_gap=40) is False


def test_is_left_of_false_for_different_lines() -> None:
    label = BoundingBox(x=100, y=200, width=80, height=20)
    target = BoundingBox(x=190, y=400, width=200, height=20)
    assert is_left_of(label, target, max_gap=40) is False


def test_is_above_true_for_overlapping_columns() -> None:
    label = BoundingBox(x=100, y=200, width=150, height=20)
    target = BoundingBox(x=110, y=225, width=150, height=20)
    assert is_above(label, target, max_gap=40) is True


def test_is_above_false_when_columns_dont_overlap() -> None:
    label = BoundingBox(x=100, y=200, width=50, height=20)
    target = BoundingBox(x=400, y=225, width=150, height=20)
    assert is_above(label, target, max_gap=40) is False


def test_group_tokens_into_lines_clusters_same_row() -> None:
    tokens = (
        _token("Full", x=100, y=200),
        _token("Name", x=145, y=200),
        _token("Address", x=100, y=260),
    )
    lines = group_tokens_into_lines(tokens)

    assert len(lines) == 2
    assert [t.text for t in lines[0]] == ["Full", "Name"]
    assert [t.text for t in lines[1]] == ["Address"]


def test_group_tokens_into_lines_orders_top_to_bottom() -> None:
    tokens = (
        _token("Second", x=100, y=300),
        _token("First", x=100, y=100),
    )
    lines = group_tokens_into_lines(tokens)

    assert lines[0][0].text == "First"
    assert lines[1][0].text == "Second"


def test_union_bounding_box_spans_all_inputs() -> None:
    boxes = [
        BoundingBox(x=10, y=10, width=20, height=10),
        BoundingBox(x=50, y=5, width=10, height=30),
    ]
    union = union_bounding_box(boxes)

    assert union.x == 10
    assert union.y == 5
    assert union.width == 50  # right edge at 60, left edge at 10
    assert union.height == 30
