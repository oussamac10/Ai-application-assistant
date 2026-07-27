from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.field_detection.extraction import extract_native_document_input
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


def _create_unknown_digital_form_pdf(filepath: str) -> None:
    """Builds a PDF matching the reported unknown-digital-form.pdf shape:
    a checkbox choice group, a radio choice group, a label followed by a
    large blank region, a checkbox-marked confirmation sentence, two
    labels ("Signature:"/"Date:") sharing one physical line, and a footer
    document-identifier line that must never be detected as a real field.
    """
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(100, 750, "Request category")
    c.drawString(100, 725, "[_] Housing")
    c.drawString(100, 700, "[_] Education")
    c.drawString(100, 675, "[_] Medical")

    c.drawString(100, 640, "Preferred contact method")
    c.drawString(100, 615, "(_) Email")
    c.drawString(100, 590, "(_) Phone")
    c.drawString(100, 565, "(_) Post")

    c.drawString(100, 530, "Describe your situation:")

    c.drawString(100, 350, "[_]")
    c.drawString(120, 350, "I confirm that the information provided above is accurate.")

    c.drawString(100, 310, "Signature:")
    c.drawString(400, 310, "Date:")

    c.drawString(100, 40, "Test document ID: TD-2024-0007")

    c.showPage()
    c.save()


def test_unknown_digital_form_detects_all_expected_fields(tmp_path: Path) -> None:
    pdf_path = tmp_path / "unknown-digital-form.pdf"
    _create_unknown_digital_form_pdf(str(pdf_path))
    document = extract_native_document_input(pdf_path)

    result = LocalFieldDetectionProvider().detect(document)
    fields_by_label = {f.label: f for f in result.fields}

    assert set(fields_by_label) == {
        "Request category",
        "Preferred contact method",
        "Describe your situation",
        "I confirm that the information provided above is accurate.",
        "Signature",
        "Date",
    }

    category = fields_by_label["Request category"]
    assert category.field_type == "multiple_choice"
    assert category.multiple is True
    assert category.options == ("Housing", "Education", "Medical")

    contact_method = fields_by_label["Preferred contact method"]
    assert contact_method.field_type == "radio"
    assert contact_method.multiple is False
    assert contact_method.options == ("Email", "Phone", "Post")

    situation = fields_by_label["Describe your situation"]
    assert situation.field_type == "multiline_text"

    confirmation = fields_by_label[
        "I confirm that the information provided above is accurate."
    ]
    assert confirmation.field_type == "checkbox"

    assert fields_by_label["Signature"].field_type == "signature"
    assert fields_by_label["Date"].field_type == "date"

    for field in result.fields:
        assert 0.0 <= field.confidence <= 1.0


def test_unknown_digital_form_excludes_footer_document_id(tmp_path: Path) -> None:
    pdf_path = tmp_path / "unknown-digital-form.pdf"
    _create_unknown_digital_form_pdf(str(pdf_path))
    document = extract_native_document_input(pdf_path)

    result = LocalFieldDetectionProvider().detect(document)

    labels = {f.label for f in result.fields}
    assert not any("document id" in label.lower() for label in labels)
    assert not any("TD-2024" in (f.existing_value or "") for f in result.fields)


def test_checkbox_choice_group_options_preserve_display_order() -> None:
    tokens = (
        _token("Request category", x=100, y=100, width=150, height=14),
        _token("[_]", x=100, y=125, width=20, height=14),
        _token("Housing", x=125, y=125, width=60, height=14),
        _token("[_]", x=100, y=150, width=20, height=14),
        _token("Education", x=125, y=150, width=70, height=14),
        _token("[_]", x=100, y=175, width=20, height=14),
        _token("Medical", x=125, y=175, width=60, height=14),
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
    assert field.field_type == "multiple_choice"
    assert field.options == ("Housing", "Education", "Medical")


def test_radio_choice_group_is_single_choice() -> None:
    tokens = (
        _token("Preferred contact method", x=100, y=100, width=200, height=14),
        _token("(_)", x=100, y=125, width=20, height=14),
        _token("Email", x=125, y=125, width=50, height=14),
        _token("(_)", x=100, y=150, width=20, height=14),
        _token("Phone", x=125, y=150, width=50, height=14),
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
    assert field.field_type == "radio"
    assert field.multiple is False
    assert field.options == ("Email", "Phone")


def test_option_labels_do_not_become_separate_fields() -> None:
    tokens = (
        _token("Request category", x=100, y=100, width=150, height=14),
        _token("[_]", x=100, y=125, width=20, height=14),
        _token("Housing", x=125, y=125, width=60, height=14),
        _token("[_]", x=100, y=150, width=20, height=14),
        _token("Education", x=125, y=150, width=70, height=14),
    )
    document = DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(page_number=1, width=612, height=792, tokens=tokens),
        ),
    )

    result = LocalFieldDetectionProvider().detect(document)

    labels = [f.label for f in result.fields]
    assert "Housing" not in labels
    assert "Education" not in labels
