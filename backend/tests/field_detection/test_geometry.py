from app.field_detection.geometry import (
    group_tokens_into_lines,
    is_above,
    is_close_below,
    is_large_vertical_gap,
    is_left_of,
    split_line_into_segments,
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


def test_split_line_into_segments_keeps_one_label_together() -> None:
    tokens = [
        _token("Full", x=100, y=200, width=40, height=14),
        _token("Name:", x=145, y=200, width=45, height=14),
        _token("John", x=195, y=200, width=40, height=14),
    ]
    segments = split_line_into_segments(tokens)
    assert len(segments) == 1
    assert [t.text for t in segments[0]] == ["Full", "Name:", "John"]


def test_split_line_into_segments_splits_two_labels_sharing_one_line() -> None:
    tokens = [
        _token("Signature:", x=100, y=310, width=60, height=14),
        _token("Date:", x=400, y=310, width=35, height=14),
    ]
    segments = split_line_into_segments(tokens)
    assert len(segments) == 2
    assert [t.text for t in segments[0]] == ["Signature:"]
    assert [t.text for t in segments[1]] == ["Date:"]


def test_is_close_below_true_for_adjacent_option_line() -> None:
    heading = BoundingBox(x=100, y=100, width=150, height=14)
    option = BoundingBox(x=100, y=125, width=100, height=14)
    assert is_close_below(heading, option) is True


def test_is_close_below_false_for_distant_line() -> None:
    heading = BoundingBox(x=100, y=100, width=150, height=14)
    option = BoundingBox(x=100, y=500, width=100, height=14)
    assert is_close_below(heading, option) is False


def test_is_large_vertical_gap_true_for_blank_region() -> None:
    label = BoundingBox(x=100, y=100, width=150, height=14)
    next_line = BoundingBox(x=100, y=280, width=150, height=14)
    assert is_large_vertical_gap(label, next_line) is True


def test_is_large_vertical_gap_false_for_normal_line_spacing() -> None:
    label = BoundingBox(x=100, y=200, width=150, height=14)
    next_line = BoundingBox(x=100, y=225, width=150, height=14)
    assert is_large_vertical_gap(label, next_line) is False
