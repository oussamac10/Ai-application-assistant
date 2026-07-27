from app.field_detection.labeling import build_line_groups, build_line_phrases
from app.field_detection.providers.base import BoundingBox, DetectionToken


def _token(
    text: str, x: float, y: float, width: float = 40, height: float = 14
) -> DetectionToken:
    return DetectionToken(
        text=text,
        confidence=1.0,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        source="native",
    )


def test_build_line_groups_splits_two_labels_sharing_one_line() -> None:
    tokens = (
        _token("Signature:", x=100, y=310, width=60),
        _token("Date:", x=400, y=310, width=35),
    )
    groups = build_line_groups(1, tokens)

    assert len(groups) == 1
    assert len(groups[0]) == 2
    assert groups[0][0].text == "Signature"
    assert groups[0][1].text == "Date"


def test_build_line_phrases_flattens_groups() -> None:
    tokens = (
        _token("Signature:", x=100, y=310, width=60),
        _token("Date:", x=400, y=310, width=35),
        _token("Email:", x=100, y=200, width=50),
    )
    phrases = build_line_phrases(1, tokens)

    assert [p.text for p in phrases] == ["Email", "Signature", "Date"]
