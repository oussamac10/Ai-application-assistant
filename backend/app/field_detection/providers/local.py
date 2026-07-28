"""LocalFieldDetectionProvider — deterministic, rules-based field detection.

No AI or cloud dependency. Two mutually exclusive top-level strategies:

- If the document has AcroForm widgets, they are authoritative: each widget
  already carries a structural field_type, so detection here is about
  finding its nearby label and refining "text" widgets via label wording.
- Otherwise (plain digital text or OCR output), text is processed in three
  ordered passes per page, each pass consuming the lines it recognizes so
  later passes never re-derive a field from the same evidence:

  1. Choice groups — a heading line followed by consecutive marker-labeled
     option lines (checkbox brackets -> multiple_choice, radio parens ->
     single-choice "radio"), read in display order.
  2. Confirmation checkboxes — a first-person consent/confirmation sentence
     accompanied by checkbox-marker geometry on the same line.
  3. Everything else — colon-terminated label/value segments (already split
     per physical line by labeling.build_line_groups, so e.g. "Signature:"
     and "Date:" sharing one line become separate segments), plus a
     colon-less label immediately followed by a large blank vertical gap
     (classified as multiline_text). Footer/margin metadata lines are
     excluded from this pass by keyword+position, never by exact text.

Confidence always reflects how much of this evidence was actually found;
normalization.py downgrades anything below the low-confidence threshold to
"unknown" rather than guessing.
"""

from __future__ import annotations

from app.field_detection.classification import (
    acroform_widget_confidence,
    choice_group_confidence,
    classify_label,
    classify_value_pattern,
    is_blank_run,
    is_confirmation_sentence,
    is_footer_metadata,
    is_probably_prose_label,
    marker_type,
)
from app.field_detection.geometry import (
    CLOSE_BELOW_RATIO,
    is_close_below,
    is_large_vertical_gap,
    union_bounding_box,
)
from app.field_detection.labeling import (
    LinePhrase,
    build_line_groups,
    build_line_phrases,
    find_nearest_label_for_box,
)
from app.field_detection.normalization import (
    deduplicate_candidates,
    downgrade_low_confidence,
    normalize_field_name,
    sort_candidates_deterministically,
)
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionResult,
    DetectionToken,
)

_ACROFORM_TYPE_MAP = {
    "checkbox": "checkbox",
    "radio": "radio",
    "choice": "select",
    "signature": "signature",
    "text": "text",
}

# German sentence-embedded blank triggers (see
# LocalFieldDetectionProvider._detect_inline_blank_fields). Deterministic
# and deliberately narrow — matched only against the last word of a
# segment (date) or the first word of the following segment (currency
# unit), never against arbitrary prose.
_INLINE_DATE_TRIGGER_WORDS = frozenset({"am", "datum", "termin"})
_INLINE_CURRENCY_TRIGGER_WORDS = frozenset(
    {
        "beträgt",
        "betraegt",
        "kostet",
        "betragen",
        "miete",
        "kaution",
        "nebenkosten",
        "vorauszahlung",
        "gesamtmiete",
    }
)
_INLINE_CURRENCY_SUFFIX_WORDS = frozenset({"euro", "eur", "€"})

_HUMANIZE_UNDERSCORE = str.maketrans("_-", "  ")


def _humanize_field_name(field_name: str) -> str:
    spaced = field_name.translate(_HUMANIZE_UNDERSCORE).strip()
    return spaced.title() if spaced else field_name


def _line_box(segments: list[LinePhrase]) -> BoundingBox:
    return union_bounding_box([s.bounding_box for s in segments])


def _line_tokens(segments: list[LinePhrase]) -> list[DetectionToken]:
    tokens: list[DetectionToken] = []
    for segment in segments:
        tokens.extend(segment.tokens)
    return tokens


def _extract_single_option(tokens: list[DetectionToken]) -> tuple[str, str] | None:
    """Parses one physical line's tokens as a single marker + label option
    (e.g. "[_] Housing"). Returns None if it isn't exactly one marker plus
    a non-empty label.
    """
    marker_tokens = [t for t in tokens if marker_type(t.text) is not None]
    if len(marker_tokens) != 1:
        return None

    kind = marker_type(marker_tokens[0].text)
    label_tokens = sorted(
        (t for t in tokens if marker_type(t.text) is None),
        key=lambda t: t.bounding_box.x,
    )
    label = " ".join(t.text for t in label_tokens).strip()
    if not label or kind is None:
        return None
    return kind, label


class LocalFieldDetectionProvider:
    provider_name = "local"
    provider_version = "1"

    def detect(self, document: DetectionDocumentInput) -> DetectionResult:
        if document.acroform_widgets:
            candidates = self._detect_from_acroform(document)
        else:
            candidates = self._detect_from_text_lines(document)

        candidates = [downgrade_low_confidence(c) for c in candidates]
        candidates = deduplicate_candidates(candidates)
        candidates = sort_candidates_deterministically(candidates)

        return DetectionResult(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            fields=tuple(candidates),
        )

    def _phrases_by_page(
        self, document: DetectionDocumentInput
    ) -> dict[int, list[LinePhrase]]:
        return {
            page.page_number: build_line_phrases(page.page_number, page.tokens)
            for page in document.pages
        }

    def _detect_from_acroform(
        self, document: DetectionDocumentInput
    ) -> list[DetectedFieldCandidate]:
        phrases_by_page = self._phrases_by_page(document)
        candidates: list[DetectedFieldCandidate] = []

        for index, widget in enumerate(document.acroform_widgets):
            page_phrases = phrases_by_page.get(widget.page_number, [])
            nearest_label = find_nearest_label_for_box(widget.rect, page_phrases)

            mapped_type = _ACROFORM_TYPE_MAP.get(widget.field_type, "text")
            if nearest_label and nearest_label.text:
                label = nearest_label.text
            else:
                label = _humanize_field_name(widget.field_name)

            if mapped_type == "text":
                mapped_type = classify_label(label)

            confidence = acroform_widget_confidence(
                mapped_type, label_found=nearest_label is not None
            )

            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"acroform-{widget.page_number}-{index}",
                    page_number=widget.page_number,
                    label=label,
                    normalized_name=normalize_field_name(widget.field_name or label),
                    field_type=mapped_type,
                    confidence=confidence,
                    source="acroform",
                    required=widget.required,
                    label_bounding_box=nearest_label.bounding_box
                    if nearest_label
                    else None,
                    input_bounding_box=widget.rect,
                )
            )

        return candidates

    def _detect_from_text_lines(
        self, document: DetectionDocumentInput
    ) -> list[DetectedFieldCandidate]:
        candidates: list[DetectedFieldCandidate] = []

        for page in document.pages:
            line_groups = build_line_groups(page.page_number, page.tokens)

            choice_candidates, consumed = self._detect_choice_groups(
                page.page_number, line_groups
            )
            candidates.extend(choice_candidates)

            candidates.extend(
                self._detect_confirmation_checkboxes(
                    page.page_number, line_groups, consumed
                )
            )

            candidates.extend(
                self._detect_label_above_blank_line_fields(
                    page.page_number, line_groups, consumed
                )
            )

            candidates.extend(
                self._detect_inline_blank_fields(
                    page.page_number, line_groups, consumed
                )
            )

            candidates.extend(self._detect_normal_fields(page, line_groups, consumed))

        return candidates

    def _detect_choice_groups(
        self, page_number: int, line_groups: list[list[LinePhrase]]
    ) -> tuple[list[DetectedFieldCandidate], set[int]]:
        candidates: list[DetectedFieldCandidate] = []
        consumed: set[int] = set()
        line_boxes = [_line_box(group) for group in line_groups]

        for heading_index, heading_group in enumerate(line_groups):
            if heading_index in consumed:
                continue

            heading_tokens = _line_tokens(heading_group)
            if not heading_tokens or any(
                marker_type(t.text) is not None for t in heading_tokens
            ):
                continue

            heading_text = " ".join(p.text for p in heading_group).strip()
            heading_text = heading_text.rstrip(":").strip()
            if not heading_text:
                continue

            options: list[tuple[str, str]] = []
            option_indices: list[int] = []
            previous_box = line_boxes[heading_index]
            cursor = heading_index + 1

            while cursor < len(line_groups):
                if cursor in consumed:
                    break
                candidate_box = line_boxes[cursor]
                if not is_close_below(previous_box, candidate_box):
                    break

                # A physical line can hold one option (vertically stacked
                # groups) or several (options laid out side by side, each
                # its own segment after split_line_into_segments) — either
                # way every segment on the line must parse as a marker +
                # label pair, or this line isn't part of the group.
                line_options: list[tuple[str, str]] = []
                for segment in line_groups[cursor]:
                    option = _extract_single_option(list(segment.tokens))
                    if option is None:
                        line_options = []
                        break
                    line_options.append(option)
                if not line_options:
                    break

                options.extend(line_options)
                option_indices.append(cursor)
                previous_box = candidate_box
                cursor += 1

            if len(options) < 2:
                continue

            marker_kinds = {kind for kind, _ in options}
            marker_kind = options[0][0] if len(marker_kinds) == 1 else None
            if marker_kind == "checkbox":
                field_type = "multiple_choice"
                multiple = True
            elif marker_kind == "radio":
                field_type = "radio"
                multiple = False
            else:
                # Mixed marker kinds in one group is ambiguous evidence —
                # never invent a choice type from conflicting geometry.
                continue

            consumed.add(heading_index)
            consumed.update(option_indices)

            option_boxes = [line_boxes[i] for i in option_indices]
            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"choice-{page_number}-{heading_index}",
                    page_number=page_number,
                    label=heading_text,
                    normalized_name=normalize_field_name(heading_text),
                    field_type=field_type,
                    confidence=choice_group_confidence(marker_kind),
                    source=heading_tokens[0].source,
                    multiple=multiple,
                    label_bounding_box=line_boxes[heading_index],
                    input_bounding_box=union_bounding_box(option_boxes),
                    options=tuple(label for _, label in options),
                )
            )

        return candidates, consumed

    def _detect_confirmation_checkboxes(
        self,
        page_number: int,
        line_groups: list[list[LinePhrase]],
        consumed: set[int],
    ) -> list[DetectedFieldCandidate]:
        candidates: list[DetectedFieldCandidate] = []

        for index, group in enumerate(line_groups):
            if index in consumed:
                continue

            tokens = _line_tokens(group)
            if not any(marker_type(t.text) == "checkbox" for t in tokens):
                continue

            text_tokens = [t for t in tokens if marker_type(t.text) is None]
            sentence = " ".join(t.text for t in text_tokens).strip()
            if not is_confirmation_sentence(sentence):
                continue

            consumed.add(index)
            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"confirm-{page_number}-{index}",
                    page_number=page_number,
                    label=sentence,
                    normalized_name=normalize_field_name(sentence),
                    field_type="checkbox",
                    confidence=choice_group_confidence("checkbox"),
                    source=tokens[0].source,
                    label_bounding_box=_line_box(group),
                )
            )

        return candidates

    def _detect_normal_fields(
        self,
        page: DetectionPageInput,
        line_groups: list[list[LinePhrase]],
        consumed: set[int],
    ) -> list[DetectedFieldCandidate]:
        candidates: list[DetectedFieldCandidate] = []
        line_boxes = [_line_box(group) for group in line_groups]

        for index, group in enumerate(line_groups):
            if index in consumed:
                continue

            next_box = line_boxes[index + 1] if index + 1 < len(line_boxes) else None

            for segment_index, phrase in enumerate(group):
                if not phrase.text:
                    continue
                if is_footer_metadata(phrase.text, phrase.bounding_box.y, page.height):
                    continue

                # A label needs either a colon or its own detected blank-
                # run marker (dots/underscores — see
                # classification.is_blank_run) to be treated as an actual
                # field, as opposed to a title/subtitle/instructional
                # sentence — plain prose has neither and is excluded here
                # rather than guessed at from spacing alone. Only a line
                # consisting of a single label (no sibling segment sharing
                # the physical line, e.g. not the "Signature: / Date:"
                # case) can be a multiline label — a split-line segment is
                # a short discrete field, never a blank-area label.
                if not (phrase.has_colon or phrase.has_blank_marker):
                    continue
                if not phrase.text:
                    continue
                # A colon-terminated sentence that merely happens to end
                # with ":" (e.g. introducing a list) is not a field label —
                # only guard the colon path; a blank-run marker is strong
                # enough evidence on its own regardless of label length.
                if (
                    phrase.has_colon
                    and not phrase.has_blank_marker
                    and is_probably_prose_label(phrase.text)
                ):
                    continue

                # A blank-run marker (e.g. "……………") is a placeholder for
                # where the user will write their answer — it is never
                # real prefilled data, so it must never be surfaced as
                # existing_value (which the UI would otherwise show as a
                # pre-filled answer to confirm).
                trailing_is_blank_only = bool(phrase.trailing_text) and all(
                    is_blank_run(part) or not part
                    for part in phrase.trailing_text.split()
                )

                has_large_gap_below = (
                    len(group) == 1
                    and next_box is not None
                    and is_large_vertical_gap(phrase.bounding_box, next_box)
                )

                if has_large_gap_below and not phrase.trailing_text:
                    field_type = "multiline_text"
                    confidence = 0.75
                else:
                    value_type = (
                        classify_value_pattern(phrase.trailing_text)
                        if phrase.trailing_text and not trailing_is_blank_only
                        else None
                    )
                    label_type = classify_label(phrase.text)

                    if value_type is not None:
                        field_type = value_type
                        confidence = 0.8
                    elif label_type != "text":
                        field_type = label_type
                        confidence = 0.65
                    elif phrase.has_blank_marker:
                        # No keyword matched, but a real blank-run marker
                        # is direct layout evidence this is a genuine
                        # fillable field (not a guess from spacing alone).
                        field_type = "text"
                        confidence = 0.6
                    else:
                        field_type = "text"
                        confidence = 0.55

                candidates.append(
                    DetectedFieldCandidate(
                        candidate_key=(
                            f"page{page.page_number}-line{index}-seg{segment_index}"
                        ),
                        page_number=page.page_number,
                        label=phrase.text,
                        normalized_name=normalize_field_name(phrase.text),
                        field_type=field_type,
                        confidence=confidence,
                        source=phrase.source,
                        label_bounding_box=phrase.bounding_box,
                        existing_value=(
                            None
                            if trailing_is_blank_only
                            else (phrase.trailing_text or None)
                        ),
                    )
                )

        return candidates

    def _detect_label_above_blank_line_fields(
        self,
        page_number: int,
        line_groups: list[list[LinePhrase]],
        consumed: set[int],
    ) -> list[DetectedFieldCandidate]:
        """A label on its own line, immediately followed by a line that is
        *only* a blank-run marker (dots/underscores) — a layout German
        bureaucratic forms commonly use for wider input areas ("IBAN" on
        one line, the fillable underline directly below it), with no colon
        and no same-line marker at all."""
        candidates: list[DetectedFieldCandidate] = []
        line_boxes = [_line_box(group) for group in line_groups]

        for index, group in enumerate(line_groups):
            if index in consumed or len(group) != 1:
                continue
            phrase = group[0]
            if phrase.has_colon or phrase.has_blank_marker or not phrase.text:
                continue
            if is_probably_prose_label(phrase.text) or is_blank_run(phrase.text):
                continue

            next_index = index + 1
            if next_index >= len(line_groups) or next_index in consumed:
                continue
            next_group = line_groups[next_index]
            if len(next_group) != 1:
                continue
            next_phrase = next_group[0]
            if not next_phrase.text or not is_blank_run(next_phrase.text):
                continue
            if not is_close_below(
                line_boxes[index], line_boxes[next_index], CLOSE_BELOW_RATIO
            ):
                continue

            consumed.add(index)
            consumed.add(next_index)

            label_type = classify_label(phrase.text)
            field_type = label_type
            confidence = 0.65 if label_type != "text" else 0.55

            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"page{page_number}-labelabove-{index}",
                    page_number=page_number,
                    label=phrase.text,
                    normalized_name=normalize_field_name(phrase.text),
                    field_type=field_type,
                    confidence=confidence,
                    source=phrase.source,
                    label_bounding_box=phrase.bounding_box,
                    input_bounding_box=next_phrase.bounding_box,
                )
            )

        return candidates

    def _detect_inline_blank_fields(
        self,
        page_number: int,
        line_groups: list[list[LinePhrase]],
        consumed: set[int],
    ) -> list[DetectedFieldCandidate]:
        """Sentence-embedded blanks: a date or amount value left blank in
        the middle of a prose sentence (e.g. "Das Vertragsverhältnis
        beginnt am ... und endet am ...", "Die monatliche Grundmiete
        beträgt ... Euro."). Exporters commonly leave enough horizontal
        space for handwriting that `split_line_into_segments` already
        splits the sentence around it — detected here only when a segment
        ends with a recognized German date/amount trigger word (or the
        following segment starts with a currency unit), never from
        arbitrary prose, so normal legal paragraphs are never mistaken for
        fields."""
        candidates: list[DetectedFieldCandidate] = []

        for index, group in enumerate(line_groups):
            if index in consumed or len(group) < 2:
                continue

            found_any = False
            for segment_index in range(len(group) - 1):
                current = group[segment_index]
                following = group[segment_index + 1]
                current_words = current.text.split()
                if not current_words:
                    continue
                last_word = current_words[-1].strip(".,;:").lower()
                following_words = following.text.split() if following.text else []
                following_first = (
                    following_words[0].strip(".,;:").lower() if following_words else ""
                )

                field_type: str | None = None
                if last_word in _INLINE_DATE_TRIGGER_WORDS:
                    field_type = "date"
                elif following_first in _INLINE_CURRENCY_SUFFIX_WORDS:
                    lowered_current = {w.strip(".,;:").lower() for w in current_words}
                    if lowered_current & _INLINE_CURRENCY_TRIGGER_WORDS:
                        field_type = "currency"

                if field_type is None:
                    continue

                label = " ".join(current_words[-4:])
                found_any = True
                candidates.append(
                    DetectedFieldCandidate(
                        candidate_key=(
                            f"page{page_number}-inline-{index}-{segment_index}"
                        ),
                        page_number=page_number,
                        label=label,
                        normalized_name=normalize_field_name(
                            f"{label}_{index}_{segment_index}"
                        ),
                        field_type=field_type,
                        confidence=0.6,
                        source=(
                            current.tokens[0].source if current.tokens else "native"
                        ),
                        label_bounding_box=current.bounding_box,
                        input_bounding_box=following.bounding_box,
                    )
                )

            if found_any:
                consumed.add(index)

        return candidates
