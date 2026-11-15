"""Tests for geometric and key-based table row grouping in AnswerService."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.answers.services import AnswerService


def _fake_field(
    field_id: str,
    key: str,
    label: str,
    position: int,
    *,
    field_type: str = "text",
    section_name: str | None = "2 Haushaltsangehörige",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=field_id,
        key=key,
        label=label,
        position=position,
        field_type=field_type,
        required=False,
        configuration=None,
        section_name=section_name,
        options=None,
    )


@pytest.mark.asyncio
async def test_geometric_table_row_context_groups_aligned_pdf_table_rows() -> None:
    """AcroForm/visual PDF tables without <table_row_col> keys must still group
    into rows by aligned columns and regular vertical row spacing."""
    fields = [
        _fake_field(
            "f0", "txtname", "Name", 1, section_name="1 Antragstellende Person"
        ),
        # Row 1 (y ~ 668)
        _fake_field("r1c2", "txtgeburt1s1", "Geburtsdatum", 10, field_type="date"),
        _fake_field("r1c3", "txtgeschlecht1s1", "Geschlecht", 11),
        _fake_field("r1c4", "txtverwand1s1", "Verwandtschaft", 12),
        _fake_field("r1c5", "txtstaat1s1", "Staatsangehörigkeit", 13),
        # Row 2 (y ~ 691)
        _fake_field("r2c1", "txtname1s1", "Name 1S1", 20),
        _fake_field("r2c2", "txtgeburt2s1", "Geburt 2S1", 21, field_type="date"),
        _fake_field("r2c3", "txtgeschlecht2s1", "Geschlecht 2S1", 22),
        _fake_field("r2c4", "txtverwand2s1", "Verwand 2S1", 23),
        _fake_field("r2c5", "txtstaat2s1", "Staat 2S1", 24),
        # Row 3 (y ~ 716)
        _fake_field("r3c1", "txtname2s1", "Name 2S1", 30),
        _fake_field("r3c2", "txtgeburt3s1", "Geburt 3S1", 31, field_type="date"),
        _fake_field("r3c3", "txtgeschlecht3s1", "Geschlecht 3S1", 32),
        _fake_field("r3c4", "txtverwand3s1", "Verwand 3S1", 33),
        _fake_field("r3c5", "txtstaat3s1", "Staat 3S1", 34),
    ]
    boxes = {
        "txtname": (1, {"x": 67.0, "y": 309.0, "width": 200.0, "height": 15.0}),
        "txtgeburt1s1": (1, {"x": 238.0, "y": 668.0, "width": 56.0, "height": 15.0}),
        "txtgeschlecht1s1": (
            1,
            {"x": 296.0, "y": 668.0, "width": 26.0, "height": 15.0},
        ),
        "txtverwand1s1": (1, {"x": 325.0, "y": 668.0, "width": 68.0, "height": 15.0}),
        "txtstaat1s1": (1, {"x": 396.0, "y": 668.0, "width": 92.0, "height": 15.0}),
        "txtname1s1": (1, {"x": 83.0, "y": 685.0, "width": 152.0, "height": 15.0}),
        "txtgeburt2s1": (1, {"x": 238.0, "y": 691.0, "width": 56.0, "height": 15.0}),
        "txtgeschlecht2s1": (
            1,
            {"x": 296.0, "y": 691.0, "width": 26.0, "height": 15.0},
        ),
        "txtverwand2s1": (1, {"x": 325.0, "y": 691.0, "width": 68.0, "height": 15.0}),
        "txtstaat2s1": (1, {"x": 396.0, "y": 691.0, "width": 92.0, "height": 15.0}),
        "txtname2s1": (1, {"x": 83.0, "y": 710.0, "width": 152.0, "height": 15.0}),
        "txtgeburt3s1": (1, {"x": 238.0, "y": 716.0, "width": 56.0, "height": 15.0}),
        "txtgeschlecht3s1": (
            1,
            {"x": 296.0, "y": 716.0, "width": 26.0, "height": 15.0},
        ),
        "txtverwand3s1": (1, {"x": 325.0, "y": 716.0, "width": 68.0, "height": 15.0}),
        "txtstaat3s1": (1, {"x": 396.0, "y": 716.0, "width": 92.0, "height": 15.0}),
    }

    service = AnswerService(db=MagicMock())

    async def _fake_translated(rf: SimpleNamespace, *args: object) -> dict[str, object]:
        return {"label": rf.label, "options": rf.options}

    service._get_translated_field = _fake_translated  # type: ignore[method-assign]

    session = SimpleNamespace(
        user_language="en",
        source_language="de",
        output_language="de",
    )
    version = SimpleNamespace(fields=fields)

    with patch(
        "app.answers.services.get_all_field_boxes_for_session",
        return_value=boxes,
    ):
        # Non-table field returns None
        assert (
            await service._build_table_row_context(
                session=session,
                version=version,
                current_field=fields[0],  # type: ignore[arg-type]
                answers={},
            )
            is None
        )

        # Table Row 2 field returns all 5 cells of Row 2 ordered left-to-right
        ctx = await service._build_table_row_context(
            session=session,
            version=version,
            current_field=fields[6],  # type: ignore[arg-type]
            answers={},
        )

    assert ctx is not None
    assert ctx["table_title"] == "2 Haushaltsangehörige"
    assert ctx["row_index"] == 2
    assert ctx["total_rows"] == 3
    assert [item["field_key"] for item in ctx["fields"]] == [
        "txtname1s1",
        "txtgeburt2s1",
        "txtgeschlecht2s1",
        "txtverwand2s1",
        "txtstaat2s1",
    ]
