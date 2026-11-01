"""Regression tests for 2D vector-grid PDFs, compound stroked paths, rotated
margin codes, inline/wrapped yes-no questions, party banners with parenthetical
notes, vector repeated-row tables, signature cells, and colon section headings.

All fixtures are synthesized with PyMuPDF (`fitz`) primitives so every test
exercises general geometric and structural rules rather than any single form.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from app.field_detection.coverage import measure_coverage
from app.field_detection.extraction import extract_native_document_input
from app.field_detection.providers.local import LocalFieldDetectionProvider


def _detect(pdf_path: Path):
    doc_input = extract_native_document_input(pdf_path)
    result = LocalFieldDetectionProvider().detect(doc_input)
    return doc_input, result.fields


def test_compound_stroked_path_extracts_checkboxes_and_ruled_rows(
    tmp_path: Path,
) -> None:
    """PDF generators batch checkboxes (`re`) and horizontal rules (`l`) into
    a single stroked path. Row 1 and every checkbox must still be extracted
    with cell-scoped bounding boxes."""
    pdf = tmp_path / "compound_grid.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(fitz.Point(70, 88), "Antrag auf Aufenthaltstitel", fontsize=11)
    options_text = [
        (96, "zum Studium"),
        (110, "zur Erwerbstätigkeit"),
        (124, "zum Familiennachzug"),
    ]
    for y, text in options_text:
        page.insert_text(fitz.Point(84, y + 10), text, fontsize=9)

    # Single compound path combining 3 checkboxes + horizontal table rules!
    compound = page.new_shape()
    for y, _ in options_text:
        compound.draw_rect(fitz.Rect(68, y, 80, y + 12))
    for y in (200, 230, 260):
        compound.draw_line(fitz.Point(51, y), fitz.Point(567, y))
    compound.finish(color=(0, 0, 0), fill=None, width=0.7)
    compound.commit()

    # Separate vertical grid lines (index col 51..65, col divider at 355, right border 567)
    for x in (51, 65, 355, 567):
        s = page.new_shape()
        s.draw_line(fitz.Point(x, 200), fitz.Point(x, 260))
        s.finish(color=(0, 0, 0), fill=None, width=0.7)
        s.commit()

    page.insert_text(fitz.Point(56, 210), "1", fontsize=8)
    page.insert_text(fitz.Point(70, 210), "Familienname", fontsize=8)
    page.insert_text(fitz.Point(360, 210), "ggf. Geburtsname", fontsize=8)

    page.insert_text(fitz.Point(56, 240), "2", fontsize=8)
    page.insert_text(fitz.Point(70, 240), "Vorname(n)", fontsize=8)
    page.insert_text(fitz.Point(360, 240), "Augenfarbe", fontsize=8)

    doc.save(pdf)
    doc.close()

    _doc_in, fields = _detect(pdf)
    labels = [f.label for f in fields]

    choice_fields = [f for f in fields if len(f.options) == 3]
    assert len(choice_fields) == 1
    assert choice_fields[0].options == (
        "zum Studium",
        "zur Erwerbstätigkeit",
        "zum Familiennachzug",
    )

    assert "Familienname" in labels
    assert "ggf. Geburtsname" in labels
    assert "Vorname(n)" in labels
    assert "Augenfarbe" in labels

    fam = next(f for f in fields if f.label == "Familienname")
    geb = next(f for f in fields if f.label == "ggf. Geburtsname")
    assert fam.input_bounding_box is not None
    assert geb.input_bounding_box is not None
    assert fam.input_bounding_box.width < 310
    assert fam.input_bounding_box.height >= 12
    assert geb.input_bounding_box.x >= 354
    assert geb.input_bounding_box.width < 230
    assert geb.input_bounding_box.height >= 12


def test_rotated_vertical_margin_code_is_excluded_from_horizontal_labels(
    tmp_path: Path,
) -> None:
    """90-degree vertical form IDs in the page margin must never bleed into
    adjacent horizontal row labels."""
    pdf = tmp_path / "rotated_margin.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Vertical form code along bottom-left margin
    page.insert_text(
        fitz.Point(30, 800),
        "32/41-1268-2604InV",
        fontsize=8,
        rotate=90,
    )

    s = page.new_shape()
    s.draw_line(fitz.Point(65, 760), fitz.Point(567, 760))
    s.draw_line(fitz.Point(65, 795), fitz.Point(567, 795))
    s.draw_line(fitz.Point(65, 760), fitz.Point(65, 795))
    s.draw_line(fitz.Point(355, 760), fitz.Point(355, 795))
    s.draw_line(fitz.Point(567, 760), fitz.Point(567, 795))
    s.finish(color=(0, 0, 0), fill=None, width=0.7)
    s.commit()

    page.insert_text(fitz.Point(70, 771), "Familienname", fontsize=8)
    page.insert_text(fitz.Point(360, 771), "Vorname(n)", fontsize=8)

    doc.save(pdf)
    doc.close()

    doc_in, fields = _detect(pdf)
    all_token_texts = [t.text for t in doc_in.pages[0].tokens]
    assert "32/41-1268-2604InV" not in all_token_texts
    assert not any("1268" in f.label or "1268" in f.normalized_name for f in fields)
    assert [f.label for f in fields] == ["Familienname", "Vorname(n)"]


def test_inline_and_multiline_yes_no_questions_preserve_distinct_labels_and_option_bbox(
    tmp_path: Path,
) -> None:
    """Multiple inline or 2-line wrapped `?` questions answered by `ja / nein`
    must keep their distinct question labels (never collapsing into a single
    `"Yes or no"` field) and highlight only the checkbox options span."""
    pdf = tmp_path / "yes_no_questions.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Q24 inline
    page.insert_text(
        fitz.Point(54, 95),
        "24 Wurde gegen Sie ein Ermittlungsverfahren eingeleitet?",
        fontsize=9,
    )
    page.insert_text(fitz.Point(393, 95), "ja", fontsize=9)
    page.insert_text(fitz.Point(450, 95), "nein", fontsize=9)

    # Follow-up inline
    page.insert_text(
        fitz.Point(70, 110),
        "Wenn ja, wurde ein Urteil gegen Sie erlassen?",
        fontsize=9,
    )
    page.insert_text(fitz.Point(393, 110), "ja", fontsize=9)
    page.insert_text(fitz.Point(450, 110), "nein", fontsize=9)

    # Q25 wrapped across 2 lines directly above ja/nein
    page.insert_text(fitz.Point(54, 150), "25", fontsize=9)
    page.insert_text(
        fitz.Point(70, 150),
        "Sind Sie in der Bundesrepublik Deutschland ausgewiesen oder abgeschoben oder ist ein Antrag",
        fontsize=9,
    )
    page.insert_text(
        fitz.Point(70, 160),
        "auf Aufenthaltstitel abgelehnt worden?",
        fontsize=9,
    )
    page.insert_text(fitz.Point(84, 173), "ja", fontsize=9)
    page.insert_text(fitz.Point(141, 173), "nein", fontsize=9)

    s = page.new_shape()
    for x, y in (
        (378, 85),
        (435, 85),
        (378, 100),
        (435, 100),
        (68, 163),
        (125, 163),
    ):
        s.draw_rect(fitz.Rect(x, y, x + 12, y + 12))
    s.finish(color=(0, 0, 0), fill=None, width=0.7)
    s.commit()

    doc.save(pdf)
    doc.close()

    _doc_in, fields = _detect(pdf)
    radio_fields = [f for f in fields if f.field_type == "radio"]
    assert len(radio_fields) == 3
    assert all(f.label != "Yes or no" for f in radio_fields)
    assert any("Ermittlungsverfahren" in f.label for f in radio_fields)
    assert any("Urteil" in f.label for f in radio_fields)
    assert any(
        "ausgewiesen" in f.label and "abgelehnt worden?" in f.label
        for f in radio_fields
    )

    q24 = next(f for f in radio_fields if "Ermittlungsverfahren" in f.label)
    assert q24.input_bounding_box is not None
    assert q24.input_bounding_box.x >= 370


def test_stacked_two_line_option_label_in_horizontal_checkbox_row_and_adjacent_cell(
    tmp_path: Path,
) -> None:
    """A two-line stacked option caption (`verheiratet/eingetragene` over
    `Lebenspartnerschaft`) in a horizontal checkbox row must join into one
    option without blocking the heading above, while an adjacent ruled cell
    (`seit`) becomes its own contextualized field."""
    pdf = tmp_path / "marital_row.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    s = page.new_shape()
    s.draw_line(fitz.Point(51, 357), fitz.Point(567, 357))
    s.draw_line(fitz.Point(51, 388), fitz.Point(567, 388))
    s.draw_line(fitz.Point(65, 357), fitz.Point(65, 388))
    s.draw_line(fitz.Point(449, 359), fitz.Point(449, 388))
    s.draw_line(fitz.Point(567, 357), fitz.Point(567, 388))
    for x in (68, 114, 238, 296):
        s.draw_rect(fitz.Rect(x, 375, x + 12, 387))
    s.finish(color=(0, 0, 0), fill=None, width=0.7)
    s.commit()

    page.insert_text(fitz.Point(58, 367), "6", fontsize=8)
    page.insert_text(fitz.Point(70, 367), "Familienstand", fontsize=8)
    page.insert_text(fitz.Point(84, 385), "ledig", fontsize=8)
    page.insert_text(fitz.Point(130, 375), "verheiratet/eingetragene", fontsize=8)
    page.insert_text(fitz.Point(130, 385), "Lebenspartnerschaft", fontsize=8)
    page.insert_text(fitz.Point(253, 385), "verwitwet", fontsize=8)
    page.insert_text(fitz.Point(311, 385), "geschieden", fontsize=8)
    page.insert_text(fitz.Point(453, 367), "seit", fontsize=8)

    doc.save(pdf)
    doc.close()

    _doc_in, fields = _detect(pdf)
    choice = next(f for f in fields if f.options)
    assert "verheiratet/eingetragene Lebenspartnerschaft" in choice.options
    assert choice.field_type == "radio"

    seit_fields = [f for f in fields if "seit" in f.label.lower()]
    assert len(seit_fields) == 1
    assert seit_fields[0].input_bounding_box is not None
    assert seit_fields[0].input_bounding_box.x >= 448


def test_party_banners_with_parenthetical_notes_and_subsections_disambiguate_repeated_fields(
    tmp_path: Path,
) -> None:
    """Party headers containing parenthetical notes and lettered sub-sections
    with 2-line ruled writing bands must disambiguate repeated field names."""
    pdf = tmp_path / "parties_and_subsections.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    s = page.new_shape()
    # Applicant row (100..130)
    s.draw_line(fitz.Point(65, 100), fitz.Point(567, 100))
    s.draw_line(fitz.Point(65, 130), fitz.Point(567, 130))
    s.draw_line(fitz.Point(355, 100), fitz.Point(355, 130))
    # Spouse banner + row (130..172, partial divider 144..172)
    s.draw_line(fitz.Point(65, 172), fitz.Point(567, 172))
    s.draw_line(fitz.Point(355, 144), fitz.Point(355, 172))
    # Father banner + row (172..214, partial divider 186..214)
    s.draw_line(fitz.Point(65, 214), fitz.Point(567, 214))
    s.draw_line(fitz.Point(355, 186), fitz.Point(355, 214))
    # Subsections a) In Deutschland & b) Im Ausland with 2-line ruled continuation bands
    for y in (260, 290, 308, 338, 356, 386, 404):
        s.draw_line(fitz.Point(65, y), fitz.Point(567, y))
    s.draw_line(fitz.Point(65, 100), fitz.Point(65, 404))
    s.draw_line(fitz.Point(567, 100), fitz.Point(567, 404))
    s.finish(color=(0, 0, 0), fill=None, width=0.7)
    s.commit()

    page.insert_text(fitz.Point(70, 110), "Familienname", fontsize=8)
    page.insert_text(fitz.Point(360, 110), "Vorname(n)", fontsize=8)

    page.insert_text(
        fitz.Point(70, 141),
        "7 Ehegatte/Eingetragene(r) Lebenspartner/-in (Angaben sind auch erforderlich, wenn diese Person im Ausland verbleibt.):",
        fontsize=8,
    )
    page.insert_text(fitz.Point(70, 152), "Familienname", fontsize=8)
    page.insert_text(fitz.Point(360, 152), "ggf. Geburtsname", fontsize=8)

    page.insert_text(
        fitz.Point(70, 183),
        "9 Vater des Antragstellers/der Antragstellerin (Angaben sind auch erforderlich, wenn diese Person im Ausland verbleibt.):",
        fontsize=8,
    )
    page.insert_text(fitz.Point(70, 194), "Familienname", fontsize=8)
    page.insert_text(fitz.Point(360, 194), "Vorname(n)", fontsize=8)

    page.insert_text(fitz.Point(70, 270), "a) In Deutschland, wann und wo?", fontsize=8)
    page.insert_text(fitz.Point(70, 318), "Grund der Strafe", fontsize=8)
    page.insert_text(fitz.Point(70, 366), "b) Im Ausland, wann und wo?", fontsize=8)

    doc.save(pdf)
    doc.close()

    _doc_in, fields = _detect(pdf)
    fam_fields = [f for f in fields if "familienname" in f.normalized_name]
    assert len(fam_fields) == 3
    assert len({f.normalized_name for f in fam_fields}) == 3

    grund = next(f for f in fields if "Grund der Strafe" in f.label)
    assert grund.input_bounding_box is not None
    # Two merged ruled writing bands -> >= 24pt tall
    assert grund.input_bounding_box.height >= 24


def test_repeated_vector_grid_table_emits_indexed_optional_fields_and_claims_checkboxes(
    tmp_path: Path,
) -> None:
    """A multi-column vector table with a tight header row + >= 2 identical
    data rows (including paired checkboxes) emits indexed optional fields and
    never leaks concatenated header text."""
    pdf = tmp_path / "children_table.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(
        fitz.Point(70, 558),
        "8 Kinder (Angaben sind auch erforderlich, wenn diese Personen im Ausland verbleiben.):",
        fontsize=8,
    )

    s = page.new_shape()
    y_lines = (562, 580, 606, 632, 658)
    x_lines = (65, 167, 245, 270, 296, 448, 567)
    for y in y_lines:
        s.draw_line(fitz.Point(65, y), fitz.Point(567, y))
    for x in x_lines:
        s.draw_line(fitz.Point(x, 562), fitz.Point(x, 658))
    for row_top in (580, 606, 632):
        s.draw_rect(fitz.Rect(251, row_top + 7, 263, row_top + 19))
        s.draw_rect(fitz.Rect(277, row_top + 7, 289, row_top + 19))
    s.finish(color=(0, 0, 0), fill=None, width=0.7)
    s.commit()

    page.insert_text(fitz.Point(95, 574), "Familienname", fontsize=7.5)
    page.insert_text(fitz.Point(187, 574), "Vorname(n)", fontsize=7.5)
    page.insert_text(fitz.Point(248, 570), "männ-", fontsize=7)
    page.insert_text(fitz.Point(252, 578), "lich", fontsize=7)
    page.insert_text(fitz.Point(275, 570), "weib-", fontsize=7)
    page.insert_text(fitz.Point(278, 578), "lich", fontsize=7)
    page.insert_text(fitz.Point(310, 574), "Geburtsdatum und -ort", fontsize=7.5)
    page.insert_text(fitz.Point(490, 574), "Wohnort", fontsize=7.5)

    doc.save(pdf)
    doc.close()

    doc_in, fields = _detect(pdf)
    cov = measure_coverage(doc_in, fields)

    assert not any("lich lich" in f.label.lower() for f in fields)
    assert cov.mark_coverage == 1.0

    row1_fields = [f for f in fields if "_1_" in f.normalized_name]
    row3_fields = [f for f in fields if "_3_" in f.normalized_name]
    assert len(row1_fields) == 5
    assert len(row3_fields) == 5
    assert all(f.required is False for f in row1_fields)

    gender_r1 = next(f for f in row1_fields if f.field_type == "radio")
    assert gender_r1.options == ("männlich", "weiblich")
    assert [f.field_type for f in row1_fields] == [
        "text",
        "text",
        "radio",
        "date",
        "address",
    ]


def test_visual_row_band_reading_order_keeps_left_checkbox_group_before_right_cell() -> (
    None
):
    """When a checkbox group on the left of a row sits slightly lower (`y=375..387`)
    than a companion text cell on the right of the same row (`y=370..387`),
    deterministic sorting must keep left-to-right reading order (`marital_status`
    before `familienstand_seit`) — and right-to-left when `rtl=True`."""
    from app.field_detection.normalization import sort_candidates_deterministically
    from app.field_detection.providers.base import BoundingBox, DetectedFieldCandidate

    right_cell = DetectedFieldCandidate(
        candidate_key="c_right",
        page_number=1,
        label="Familienstand – seit",
        normalized_name="familienstand_seit",
        field_type="text",
        confidence=0.9,
        source="native",
        input_bounding_box=BoundingBox(x=451, y=370, width=114, height=17),
    )
    left_group = DetectedFieldCandidate(
        candidate_key="c_left",
        page_number=1,
        label="Marital status",
        normalized_name="marital_status",
        field_type="radio",
        confidence=0.9,
        source="native",
        options=("ledig", "verheiratet"),
        input_bounding_box=BoundingBox(x=68, y=375, width=368, height=12),
    )

    ltr_sorted = sort_candidates_deterministically([right_cell, left_group], rtl=False)
    assert [c.normalized_name for c in ltr_sorted] == [
        "marital_status",
        "familienstand_seit",
    ]

    rtl_sorted = sort_candidates_deterministically([right_cell, left_group], rtl=True)
    assert [c.normalized_name for c in rtl_sorted] == [
        "familienstand_seit",
        "marital_status",
    ]


def test_colon_headings_over_grid_or_prose_ignored_and_signature_cell_typed_signature(
    tmp_path: Path,
) -> None:
    """Colon-terminated headings introducing a ruled grid (`Jetzige Anschrift:`)
    or legal notice (`Datenschutzrechtlicher Hinweis:`) must not become
    `input_bounding_box=None` fields, while a signature grid cell becomes a
    `signature` field with its exact cell box."""
    pdf = tmp_path / "address_and_signature_grid.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(fitz.Point(70, 641), "Jetzige Anschrift:", fontsize=9)

    s = page.new_shape()
    for y in (648, 678, 708, 745):
        s.draw_line(fitz.Point(65, y), fitz.Point(567, y))
    for x in (65, 265, 567):
        s.draw_line(fitz.Point(x, 648), fitz.Point(x, 745))
    s.finish(color=(0, 0, 0), fill=None, width=0.7)
    s.commit()

    page.insert_text(fitz.Point(70, 658), "Postleitzahl, Ort", fontsize=8)
    page.insert_text(fitz.Point(269, 658), "Straße, Hausnummer", fontsize=8)
    page.insert_text(fitz.Point(70, 688), "Telefon", fontsize=8)
    page.insert_text(fitz.Point(269, 688), "E-Mail", fontsize=8)
    page.insert_text(fitz.Point(70, 718), "Ort, Datum", fontsize=8)
    page.insert_text(fitz.Point(269, 718), "eigenhändige Unterschrift", fontsize=8)

    page.insert_text(fitz.Point(70, 768), "Datenschutzrechtlicher Hinweis:", fontsize=9)
    page.insert_text(
        fitz.Point(70, 783),
        "Nach § 86 Aufenthaltsgesetz dürfen die mit der Ausführung betrauten Behörden personenbezogene Daten erheben.",
        fontsize=8,
    )

    doc.save(pdf)
    doc.close()

    _doc_in, fields = _detect(pdf)
    normalized = {f.normalized_name for f in fields}
    assert "jetzige_anschrift" not in normalized
    assert "datenschutzrechtlicher_hinweis" not in normalized
    assert all(f.input_bounding_box is not None for f in fields)

    sig_fields = [f for f in fields if f.field_type == "signature"]
    assert len(sig_fields) == 1
    assert "Unterschrift" in sig_fields[0].label
    assert sig_fields[0].input_bounding_box is not None
    assert sig_fields[0].input_bounding_box.x >= 264
    assert sig_fields[0].input_bounding_box.height >= 18
