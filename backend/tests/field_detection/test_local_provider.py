from app.field_detection.providers.base import (
    AcroFormWidgetInput,
    BoundingBox,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionToken,
)
from app.field_detection.providers.local import LocalFieldDetectionProvider


def _token(
    text: str,
    x: float,
    y: float,
    width: float = 40,
    height: float = 20,
    source: str = "native",
) -> DetectionToken:
    return DetectionToken(
        text=text,
        confidence=1.0,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        source=source,
    )


def test_detects_colon_label_with_email_value() -> None:
    tokens = (
        _token("Email:", x=100, y=200, width=60),
        _token("john@example.com", x=170, y=200, width=200),
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(page_number=1, width=612, height=792, tokens=tokens),
        ),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert len(result.fields) == 1
    field = result.fields[0]
    assert field.label == "Email"
    assert field.normalized_name == "email"
    assert field.field_type == "email"
    assert field.existing_value == "john@example.com"
    assert field.source == "native"


def test_detects_colon_label_without_recognizable_value_defaults_to_label_guess() -> (
    None
):
    tokens = (_token("Comments:", x=100, y=200, width=80),)
    document = DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(page_number=1, width=612, height=792, tokens=tokens),
        ),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert result.fields[0].field_type == "multiline_text"


def test_ignores_lines_without_colon() -> None:
    tokens = (_token("Just a heading", x=100, y=200, width=150),)
    document = DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(page_number=1, width=612, height=792, tokens=tokens),
        ),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert result.fields == ()


def test_acroform_widget_uses_label_to_the_left() -> None:
    label_tokens = (_token("Full Name:", x=100, y=200, width=150),)
    widget = AcroFormWidgetInput(
        field_name="field_1",
        field_type="text",
        rect=BoundingBox(x=270, y=200, width=200, height=20),
        page_number=1,
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(
                page_number=1, width=612, height=792, tokens=label_tokens
            ),
        ),
        acroform_widgets=(widget,),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert len(result.fields) == 1
    field = result.fields[0]
    assert field.label == "Full Name"
    assert field.source == "acroform"
    assert field.input_bounding_box == widget.rect


def test_acroform_widget_falls_back_to_label_above_when_nothing_to_left() -> None:
    label_tokens = (_token("Email:", x=100, y=180, width=80),)
    widget = AcroFormWidgetInput(
        field_name="field_2",
        field_type="text",
        rect=BoundingBox(x=100, y=205, width=200, height=20),
        page_number=1,
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(
                page_number=1, width=612, height=792, tokens=label_tokens
            ),
        ),
        acroform_widgets=(widget,),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert result.fields[0].label == "Email"
    assert result.fields[0].field_type == "email"


def test_acroform_widget_falls_back_to_humanized_field_name_when_no_label_found() -> (
    None
):
    widget = AcroFormWidgetInput(
        field_name="date_of_birth",
        field_type="text",
        rect=BoundingBox(x=200, y=400, width=200, height=20),
        page_number=1,
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(DetectionPageInput(page_number=1, width=612, height=792, tokens=()),),
        acroform_widgets=(widget,),
    )

    result = LocalFieldDetectionProvider().detect(document)

    field = result.fields[0]
    assert field.label == "Date Of Birth"
    assert field.normalized_name == "date_of_birth"
    assert field.field_type == "date"


def test_acroform_checkbox_and_radio_widget_types_are_preserved() -> None:
    checkbox = AcroFormWidgetInput(
        field_name="agree",
        field_type="checkbox",
        rect=BoundingBox(x=100, y=100, width=20, height=20),
        page_number=1,
    )
    radio = AcroFormWidgetInput(
        field_name="gender",
        field_type="radio",
        rect=BoundingBox(x=100, y=150, width=20, height=20),
        page_number=1,
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(DetectionPageInput(page_number=1, width=612, height=792, tokens=()),),
        acroform_widgets=(checkbox, radio),
    )

    result = LocalFieldDetectionProvider().detect(document)

    field_types = {f.normalized_name: f.field_type for f in result.fields}
    assert field_types["agree"] == "checkbox"
    assert field_types["gender"] == "radio"


def test_acroform_choice_widget_maps_to_select() -> None:
    widget = AcroFormWidgetInput(
        field_name="country",
        field_type="choice",
        rect=BoundingBox(x=100, y=100, width=200, height=20),
        page_number=1,
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(DetectionPageInput(page_number=1, width=612, height=792, tokens=()),),
        acroform_widgets=(widget,),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert result.fields[0].field_type == "select"


def test_acroform_required_flag_is_preserved() -> None:
    widget = AcroFormWidgetInput(
        field_name="email",
        field_type="text",
        rect=BoundingBox(x=100, y=100, width=200, height=20),
        page_number=1,
        required=True,
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(DetectionPageInput(page_number=1, width=612, height=792, tokens=()),),
        acroform_widgets=(widget,),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert result.fields[0].required is True


def test_deterministic_ordering_across_pages() -> None:
    page2_tokens = (_token("Second Field:", x=100, y=200, width=150),)
    page1_tokens = (_token("First Field:", x=100, y=200, width=150),)
    document = DetectionDocumentInput(
        page_count=2,
        pages=(
            DetectionPageInput(
                page_number=1, width=612, height=792, tokens=page1_tokens
            ),
            DetectionPageInput(
                page_number=2, width=612, height=792, tokens=page2_tokens
            ),
        ),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert [f.page_number for f in result.fields] == [1, 2]
    assert result.fields[0].label == "First Field"
    assert result.fields[1].label == "Second Field"


def test_duplicate_labels_across_pages_are_deduplicated() -> None:
    tokens_page1 = (_token("Email:", x=100, y=200, width=80),)
    tokens_page2 = (_token("Email:", x=100, y=200, width=80),)
    document = DetectionDocumentInput(
        page_count=2,
        pages=(
            DetectionPageInput(
                page_number=1, width=612, height=792, tokens=tokens_page1
            ),
            DetectionPageInput(
                page_number=2, width=612, height=792, tokens=tokens_page2
            ),
        ),
    )

    result = LocalFieldDetectionProvider().detect(document)

    assert len(result.fields) == 1
    assert result.fields[0].page_number == 1


def test_result_is_deterministic_across_runs() -> None:
    tokens = (
        _token("Phone:", x=100, y=200, width=60),
        _token("+1 555 123 4567", x=170, y=200, width=200),
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(page_number=1, width=612, height=792, tokens=tokens),
        ),
    )

    provider = LocalFieldDetectionProvider()
    assert provider.detect(document) == provider.detect(document)
