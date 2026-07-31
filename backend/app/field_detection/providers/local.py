"""LocalFieldDetectionProvider — deterministic, rules-based field detection.

No AI or cloud dependency. Two mutually exclusive top-level strategies:

- If the document has AcroForm widgets, they are authoritative: each widget
  already carries a structural field_type, so detection here is about
  finding its nearby label and refining "text" widgets via label wording.
- Otherwise (plain digital text or OCR output), text is processed in five
  ordered passes per page, each pass consuming the lines it recognizes so
  later passes never re-derive a field from the same evidence:

  1. Choice groups — a heading line followed by consecutive marker-labeled
     option lines (checkbox brackets -> multiple_choice, radio parens ->
     single-choice "radio"), read in display order. A bare connective
     ("oder") never names a group, and a "option" that is a full sentence
     means these are independent statements rather than a choice list.
  2. Confirmation checkboxes — a first-person consent/confirmation sentence
     accompanied by checkbox-marker geometry on the same line.
  3. Label-above-blank-line — a lone label whose input area is the
     blank-run line directly beneath it.
  4. Sentence-embedded blanks — a value left blank inside running text,
     visible only as an unusually wide inter-word gap, and only accepted
     when an explicit German trigger word sits next to that gap
     ("beginnt am ___", "beträgt ___ Euro", "sind ___ Personen").
  5. Everything else — label/value segments marked by a colon and/or an
     adjacent blank run (dots/underscores), plus a colon-less label
     followed by a large blank vertical gap (classified as
     multiline_text). Footer/margin metadata lines are excluded from this
     pass by keyword+position, never by exact text.

Throughout, a candidate found under a party or "§ N" section carries that
section in its stable key (see sections.py), so the same short label
repeated for a landlord and a tenant stays two distinct fields instead of
being deduplicated down to one.

Confidence always reflects how much of this evidence was actually found;
normalization.py downgrades anything below the low-confidence threshold to
"unknown" rather than guessing.
"""

from __future__ import annotations

import logging

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
    starts_with_blank_run,
)
from app.field_detection.direction import is_rtl_language
from app.field_detection.geometry import (
    CLOSE_BELOW_RATIO,
    INLINE_BLANK_GAP_RATIO,
    is_close_below,
    is_large_vertical_gap,
    right_edge,
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
from app.field_detection.notices import filter_non_field_candidates
from app.field_detection.option_groups import (
    detect_option_groups,
    independent_boolean_options,
    match_option_set,
    strip_heading_number,
)
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionResult,
    DetectionToken,
)
from app.field_detection.requiredness import (
    OPTIONAL,
    REQUIRED,
    detect_requiredness,
    strip_requiredness_markers,
)
from app.field_detection.sections import (
    SectionContext,
    detect_context,
    is_section_heading,
)


def _contextual_label(label: str, context: SectionContext | None) -> str:
    """Prefixes a user-visible label with its party context when there is
    one ("Name" -> "Vermieter – Name"), so two same-named fields from
    different sections read unambiguously in the guided flow."""
    if context is None or not context.label_prefix:
        return label
    if context.label_prefix.lower() in label.lower():
        return label
    return f"{context.label_prefix} – {label}"


def _contextual_name(label: str, context: SectionContext | None) -> str:
    """Builds the stable, deduplication-relevant name, prefixed with the
    section's key so the same label under two sections stays two fields."""
    base = normalize_field_name(label)
    if context is None or not context.key_prefix:
        return base
    if base.startswith(f"{context.key_prefix}_"):
        return base
    return f"{context.key_prefix}_{base}"


_ACROFORM_TYPE_MAP = {
    "checkbox": "checkbox",
    "radio": "radio",
    "choice": "select",
    "signature": "signature",
    "text": "text",
}

# German sentence-embedded blank triggers (see
# LocalFieldDetectionProvider._detect_inline_blank_fields). Deterministic
# and deliberately narrow — matched only against the single word directly
# on either side of the wide gap, never against arbitrary prose.
#
# Words that, immediately *before* a wide inline gap, mark the blank as a
# date ("beginnt am ___", "endet am ___", "ist der ___").
_INLINE_DATE_TRIGGER_WORDS = frozenset({"am", "datum", "termin", "der", "zum", "bis"})
# Units that, immediately *after* a wide inline gap, mark it as an amount
# ("beträgt ___ Euro", "insgesamt ___ €").
_INLINE_CURRENCY_SUFFIX_WORDS = frozenset({"euro", "eur", "€"})
# Counted nouns that, immediately after a wide gap, mark it as an integer
# ("sind ___ Personen untergebracht").
_INLINE_COUNT_NOUNS = frozenset({"personen", "person", "zimmer", "räume", "raume"})
# How many words before the blank to keep as its label.
_INLINE_LABEL_MAX_WORDS = 5

# Bare connectives never name a choice group. German forms use a lone
# "oder" between mutually exclusive *statements* ("Eine Miete wird nicht
# gezahlt." / "Die monatliche Grundmiete beträgt ___ Euro."); treating that
# as a group label would swallow those statements as "options" and hide the
# real fields inside them.
_CONNECTIVE_ONLY_HEADINGS = frozenset(
    {"oder", "or", "und", "and", "bzw.", "bzw", "ou", "أو"}
)

# A choice option is a short phrase ("Küche", "die Waschküche inkl.
# Waschmaschine und ggf. Trockenplatz"). A complete sentence — which in
# these forms always ends with a full stop — is an independent statement,
# not an option.
# A section heading is short; a wrapped prose line is not.
logger = logging.getLogger(__name__)

_MAX_HEADING_WORDS = 8

_MAX_OPTION_WORDS = 10

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


def _row_starts_new_group(collected: tuple[str, ...], row: tuple[str, ...]) -> bool:
    """Whether `row` belongs to a different question than `collected`.

    Only a *positive* disagreement splits: both sides must match a recognised
    option set, and the sets must differ. Rows that match nothing (an ordinary
    wrapped checklist) keep accumulating, which is what keeps a long document
    list as one question.
    """
    collected_set = match_option_set(collected)
    row_set = match_option_set(row)
    return (
        collected_set is not None
        and row_set is not None
        and collected_set is not row_set
    )


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
        # Document furniture — notices, instructions, footers — looks like a
        # label but asks for nothing. Filtered before dedup so it cannot
        # occupy a normalized name a real field needs.
        candidates, _filtered = filter_non_field_candidates(candidates)
        candidates = deduplicate_candidates(candidates)
        candidates = sort_candidates_deterministically(candidates)

        return DetectionResult(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            fields=tuple(candidates),
        )

    def detect_from_tokens(
        self, document: DetectionDocumentInput
    ) -> list[DetectedFieldCandidate]:
        """Runs only the text-line passes (no AcroForm handling, no
        dedup/sort) over an already-tokenized document.

        Public because another provider may supply the tokens: the Azure
        provider converts Azure `words`/`selectionMarks` into
        `DetectionToken`s and reuses these passes wholesale, so all of the
        blank-run / section-context / inline-blank behaviour is shared
        rather than reimplemented per provider. Callers are responsible for
        deduplicating and sorting the merged result.
        """
        return self._detect_from_text_lines(document)

    def _phrases_by_page(
        self, document: DetectionDocumentInput
    ) -> dict[int, list[LinePhrase]]:
        rtl = is_rtl_language(document.language)
        return {
            page.page_number: build_line_phrases(page.page_number, page.tokens, rtl)
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

    @staticmethod
    def _build_context_map(
        line_groups: list[list[LinePhrase]],
    ) -> dict[int, SectionContext | None]:
        """Maps each line index to the section context established by the
        nearest preceding context line (a "§ N Title" heading or a short
        party-introducing line). See app/field_detection/sections.py."""
        context_map: dict[int, SectionContext | None] = {}
        active: SectionContext | None = None
        for index, group in enumerate(line_groups):
            line_text = " ".join(p.text for p in group).strip()
            established = detect_context(line_text)
            if established is not None:
                active = established
            context_map[index] = active
        return context_map

    def _detect_from_text_lines(
        self, document: DetectionDocumentInput
    ) -> list[DetectedFieldCandidate]:
        candidates: list[DetectedFieldCandidate] = []

        for page in document.pages:
            line_groups = build_line_groups(
                page.page_number, page.tokens, is_rtl_language(document.language)
            )
            context_map = self._build_context_map(line_groups)

            choice_candidates, consumed = self._detect_choice_groups(
                page.page_number, line_groups, context_map
            )
            candidates.extend(choice_candidates)

            # Option rows the heading-based pass could not claim, because the
            # form gives them no heading of their own. Runs second and only on
            # what is left, so existing behaviour is untouched — and every row
            # it claims is a row whose options would otherwise have become
            # individual free-text questions.
            candidates.extend(
                self._detect_standalone_option_groups(
                    page.page_number, line_groups, consumed
                )
            )

            candidates.extend(
                self._detect_confirmation_checkboxes(
                    page.page_number, line_groups, consumed
                )
            )

            candidates.extend(
                self._detect_label_above_blank_line_fields(
                    page.page_number, line_groups, consumed, context_map
                )
            )

            candidates.extend(
                self._detect_inline_blank_fields(
                    page.page_number, line_groups, consumed, context_map
                )
            )

            candidates.extend(
                self._detect_normal_fields(page, line_groups, consumed, context_map)
            )

        return candidates

    @staticmethod
    def _headings_by_line(line_groups: list[list[LinePhrase]]) -> dict[int, str]:
        """The nearest preceding heading-like line for each line index.

        A heading is a short line carrying no selection markers and no blank
        run — the kind of line a form uses to introduce a section.
        """
        headings: dict[int, str] = {}
        current = ""
        for index, group in enumerate(line_groups):
            text = " ".join(phrase.text for phrase in group).strip()
            tokens = _line_tokens(group)
            has_marker = any(marker_type(t.text) is not None for t in tokens)
            if (
                text
                and not has_marker
                and len(text.split()) <= _MAX_HEADING_WORDS
                and not text.rstrip().endswith(".")
            ):
                current = text
            headings[index] = current
        return headings

    def _detect_standalone_option_groups(
        self,
        page_number: int,
        line_groups: list[list[LinePhrase]],
        consumed: set[int],
    ) -> list[DetectedFieldCandidate]:
        headings = self._headings_by_line(line_groups)
        candidates: list[DetectedFieldCandidate] = []

        for group in detect_option_groups(page_number, line_groups, consumed, headings):
            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"option-group-{page_number}-{group.line_indices[0]}",
                    page_number=page_number,
                    label=group.label,
                    normalized_name=normalize_field_name(group.label),
                    field_type=group.field_type,
                    confidence=group.confidence,
                    source="native",
                    multiple=group.field_type == "multiple_choice",
                    label_bounding_box=group.bounding_box,
                    options=group.options,
                )
            )
            logger.info(
                "Option group detected: page=%d options=%d type=%s "
                "label_source=%s needs_review=%s",
                page_number,
                len(group.options),
                group.field_type,
                group.label_source,
                group.needs_review,
            )
        return candidates

    def _detect_choice_groups(
        self,
        page_number: int,
        line_groups: list[list[LinePhrase]],
        context_map: dict[int, SectionContext | None],
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
            # "5. Documents joints" -> "Documents joints". The enumeration is
            # the form's numbering, not part of the question.
            heading_text = strip_heading_number(heading_text.rstrip(":").strip())
            if not heading_text:
                continue
            if heading_text.lower() in _CONNECTIVE_ONLY_HEADINGS:
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

                # Two adjacent option rows under one heading are not
                # necessarily one question. A French form lists
                # "Français / Allemand / Anglais / Arabe" and
                # "E-mail / Téléphone / Courrier postal" on consecutive rows
                # with identical spacing under a single "Préférences de
                # communication" heading — merging them produced one
                # seven-option question mixing languages with contact
                # channels. When a row belongs to a *different* recognised
                # option set than the rows already collected, the group ends
                # here; the standalone pass then names the new row from its
                # own set.
                if options and _row_starts_new_group(
                    tuple(label for _, label in options),
                    tuple(label for _, label in line_options),
                ):
                    break

                options.extend(line_options)
                option_indices.append(cursor)
                previous_box = candidate_box
                cursor += 1

            if len(options) < 2:
                continue

            # A real choice option is a short phrase. A complete sentence
            # (ending in a full stop) means these are not options at all but
            # consecutive checkbox-prefixed *statements* — independent
            # alternative clauses whose semantics we cannot safely guess,
            # and which often contain the real fillable fields themselves
            # ("Die monatliche Grundmiete beträgt ___ Euro."). Skip the
            # group rather than invent an incompatible choice; the
            # individual lines stay available to the later passes, which is
            # how those inline amounts get detected.
            if any(
                option_label.rstrip().endswith(".")
                or len(option_label.split()) > _MAX_OPTION_WORDS
                for _, option_label in options
            ):
                continue

            marker_kinds = {kind for kind, _ in options}
            marker_kind = options[0][0] if len(marker_kinds) == 1 else None
            if marker_kind == "checkbox":
                # Checkbox glyphs usually mean "pick any", but some questions
                # are exclusive by nature whatever glyph the form drew: you
                # have one gender and one employment status. A recognised
                # exclusive set overrides the glyph; anything unrecognised
                # keeps the glyph's meaning.
                recognised = match_option_set(tuple(label for _, label in options))
                exclusive = recognised is not None and recognised.exclusive
                field_type = "radio" if exclusive else "multiple_choice"
                multiple = not exclusive
            elif marker_kind == "radio":
                field_type = "radio"
                multiple = False
            else:
                # Mixed marker kinds in one group is ambiguous evidence —
                # never invent a choice type from conflicting geometry.
                continue

            consumed.add(heading_index)
            consumed.update(option_indices)

            # The line immediately above an option list is often the tail
            # of a prose sentence rather than a real group label ("bzw. die
            # Zimmer ist/sind abschließbar."). When it reads as prose, fall
            # back to the enclosing "§ N Title" section name, which is what
            # actually describes the group.
            context = context_map.get(heading_index)
            if is_probably_prose_label(heading_text) or heading_text.endswith("."):
                if context is not None and context.title:
                    heading_text = context.title
                else:
                    # No section name to fall back on — a choice group with
                    # only a prose line to name it cannot be described
                    # safely, so skip it rather than ask an unclear
                    # question.
                    consumed.difference_update(option_indices)
                    consumed.discard(heading_index)
                    continue

            option_boxes = [line_boxes[i] for i in option_indices]
            option_labels = tuple(label for _, label in options)

            # An option carrying its own requiredness marker is not an option:
            # a choice question's requiredness belongs to the question, not to
            # individual answers. A declaration block ("I certify … *", "I
            # agree … *", "I want news (Optional)") is three independent
            # booleans, and folding it into one multiple_choice silently turns
            # two mandatory consents into "tick any of these".
            independent = independent_boolean_options(option_labels)
            if independent is not None:
                for position, (child_label, child_state) in enumerate(independent):
                    candidates.append(
                        DetectedFieldCandidate(
                            candidate_key=(
                                f"declaration-{page_number}-{heading_index}-{position}"
                            ),
                            page_number=page_number,
                            label=child_label,
                            normalized_name=_contextual_name(child_label, context),
                            field_type="checkbox",
                            confidence=choice_group_confidence(marker_kind),
                            source=heading_tokens[0].source,
                            required=(
                                True
                                if child_state == "required"
                                else False
                                if child_state == "optional"
                                else None
                            ),
                            label_bounding_box=line_boxes[option_indices[position]]
                            if position < len(option_indices)
                            else line_boxes[heading_index],
                            input_bounding_box=line_boxes[option_indices[position]]
                            if position < len(option_indices)
                            else None,
                        )
                    )
                continue

            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"choice-{page_number}-{heading_index}",
                    page_number=page_number,
                    # Requiredness is metadata the frontend renders itself; a
                    # marker left in the text shows it twice, and shows it in
                    # the document's language inside an interface in another.
                    label=strip_requiredness_markers(heading_text),
                    required=_marker_requiredness(heading_text),
                    normalized_name=_contextual_name(heading_text, context),
                    field_type=field_type,
                    confidence=choice_group_confidence(marker_kind),
                    source=heading_tokens[0].source,
                    multiple=multiple,
                    label_bounding_box=line_boxes[heading_index],
                    input_bounding_box=union_bounding_box(option_boxes),
                    options=option_labels,
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
        context_map: dict[int, SectionContext | None],
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
                # A "§ N ..." heading names a section, never a field.
                if is_section_heading(phrase.text):
                    continue
                # A segment that is itself only a blank run — or that
                # *starts* with one — is the input area, not a label.
                if is_blank_run(phrase.text) or starts_with_blank_run(phrase.text):
                    continue

                # Evidence that this is a field label: a colon (the classic
                # "Label:" form), a blank run in this same segment ("IBAN
                # ______"), or a blank run in a sibling segment on the same
                # line ("Name:" | "…………"), which is how Word-generated
                # German forms overwhelmingly lay this out.
                if not (
                    phrase.has_colon
                    or phrase.has_blank_marker
                    or phrase.has_blank_sibling
                ):
                    continue
                # A long sentence is prose, never a short field label.
                if is_probably_prose_label(phrase.text):
                    continue
                # A multi-word phrase starting in lower case is the tail of
                # a sentence wrapped from the previous line, not a label —
                # in both German and English a real label is a capitalized
                # noun phrase or an acronym ("Name:", "IBAN:", "PLZ, Ort:"),
                # whereas prose continuations read "wird folgender
                # Mietvertrag geschlossen:" / "auf folgendes Konto des
                # Vermieters gezahlt:". A single lower-case word is left
                # alone, since "email:" is a plausible label.
                if (
                    len(phrase.text.split()) >= 3
                    and phrase.text[:1].islower()
                    and not phrase.has_blank_marker
                ):
                    continue

                has_large_gap_below = (
                    len(group) == 1
                    and next_box is not None
                    and is_large_vertical_gap(phrase.bounding_box, next_box)
                )
                trailing_is_blank_only = bool(phrase.trailing_text) and all(
                    is_blank_run(part) or not part
                    for part in phrase.trailing_text.split()
                )
                has_real_trailing_value = (
                    bool(phrase.trailing_text) and not trailing_is_blank_only
                )

                if has_large_gap_below and not phrase.trailing_text:
                    field_type = "multiline_text"
                    confidence = 0.75
                else:
                    value_type = (
                        classify_value_pattern(phrase.trailing_text)
                        if has_real_trailing_value
                        else None
                    )
                    label_type = classify_label(phrase.text)

                    if value_type is not None:
                        field_type = value_type
                        confidence = 0.8
                    elif label_type != "text":
                        field_type = label_type
                        confidence = 0.65
                    elif phrase.has_blank_marker or phrase.has_blank_sibling:
                        # No keyword matched, but a real blank-run marker
                        # is direct layout evidence this is a genuine
                        # fillable field (not a guess from spacing alone).
                        field_type = "text"
                        confidence = 0.6
                    else:
                        field_type = "text"
                        confidence = 0.55

                context = context_map.get(index)
                candidates.append(
                    DetectedFieldCandidate(
                        candidate_key=(
                            f"page{page.page_number}-line{index}-seg{segment_index}"
                        ),
                        page_number=page.page_number,
                        label=_contextual_label(phrase.text, context),
                        normalized_name=_contextual_name(phrase.text, context),
                        field_type=field_type,
                        confidence=confidence,
                        source=phrase.source,
                        label_bounding_box=phrase.bounding_box,
                        # A blank-run marker (e.g. "……………") is a placeholder
                        # for where the user will write their answer — it is
                        # never real prefilled data, so it must never be
                        # surfaced as existing_value (which the UI would
                        # otherwise show as a pre-filled answer to confirm).
                        existing_value=(
                            phrase.trailing_text if has_real_trailing_value else None
                        ),
                    )
                )

        return candidates

    def _detect_label_above_blank_line_fields(
        self,
        page_number: int,
        line_groups: list[list[LinePhrase]],
        consumed: set[int],
        context_map: dict[int, SectionContext | None],
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
            # "§ 9 Sonstige Vereinbarungen" names a section; the blank area
            # under it belongs to that section, but the heading itself is
            # not a field label and must not become a question.
            if is_section_heading(phrase.text):
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
            confidence = 0.65 if label_type != "text" else 0.6

            context = context_map.get(index)
            candidates.append(
                DetectedFieldCandidate(
                    candidate_key=f"page{page_number}-labelabove-{index}",
                    page_number=page_number,
                    label=_contextual_label(phrase.text, context),
                    normalized_name=_contextual_name(phrase.text, context),
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
        context_map: dict[int, SectionContext | None],
    ) -> list[DetectedFieldCandidate]:
        """Sentence-embedded blanks: a value left blank inside running text
        (e.g. "Das Vertragsverhältnis beginnt am ____ und endet am ____.",
        "Die monatliche Grundmiete beträgt ____ Euro.", "sind ____
        Personen untergebracht").

        These blanks are pure whitespace — no dots, no underscores, no
        AcroForm widget — so the only signal is an unusually wide gap
        between two adjacent words. Measured on real Word-generated German
        forms, normal word spacing is ~0.2x line height while a deliberate
        blank is ~2.1-2.6x, so `INLINE_BLANK_GAP_RATIO` separates them with
        a wide margin (see geometry.py).

        A wide gap alone is never enough to emit a field: the words
        immediately around the gap must also match an explicit German
        trigger (a date preposition before it, a currency unit or counted
        noun after it). That keeps justified legal paragraphs — which can
        stretch inter-word spacing — from ever producing candidates.
        """
        candidates: list[DetectedFieldCandidate] = []

        for index, group in enumerate(line_groups):
            if index in consumed:
                continue

            found_any = False
            # Scan the whole physical line in reading order rather than
            # per segment: depending on how wide the blank is, segment
            # splitting may or may not have already cut the line at exactly
            # that gap, and the blank must be found either way.
            tokens = sorted(_line_tokens(group), key=lambda t: t.bounding_box.x)
            if len(tokens) >= 2:
                for token_index, (before, after) in enumerate(
                    zip(tokens, tokens[1:], strict=False)
                ):
                    gap = after.bounding_box.x - right_edge(before.bounding_box)
                    height = max(
                        before.bounding_box.height, after.bounding_box.height, 1.0
                    )
                    if gap <= INLINE_BLANK_GAP_RATIO * height:
                        continue

                    preceding_word = before.text.strip(".,;:()").lower()
                    following_word = after.text.strip(".,;:()").lower()

                    if preceding_word in _INLINE_DATE_TRIGGER_WORDS:
                        field_type = "date"
                    elif following_word in _INLINE_CURRENCY_SUFFIX_WORDS:
                        field_type = "currency"
                    elif following_word in _INLINE_COUNT_NOUNS:
                        field_type = "number"
                    else:
                        continue

                    # Label from the words leading up to the blank — that
                    # is what actually identifies the value being asked for
                    # ("Die monatliche Grundmiete beträgt").
                    words_before = [t.text for t in tokens[: token_index + 1]]
                    label = " ".join(words_before[-_INLINE_LABEL_MAX_WORDS:]).strip()
                    label = label.lstrip("[_] ").strip()
                    if following_word in _INLINE_COUNT_NOUNS:
                        label = f"{label} {after.text}".strip()
                    if not label:
                        continue

                    context = context_map.get(index)
                    found_any = True
                    candidates.append(
                        DetectedFieldCandidate(
                            candidate_key=(
                                f"page{page_number}-inline-{index}-{token_index}"
                            ),
                            page_number=page_number,
                            label=label,
                            # The label already carries the words leading up
                            # to the blank, so two blanks on one line stay
                            # distinct ("Das Vertragsverhältnis beginnt am"
                            # vs "beginnt am und endet am") without needing
                            # a positional suffix — and, deliberately, two
                            # *identically* worded blanks in one section
                            # (the same clause repeated for a befristet /
                            # unbefristet alternative) collapse into one
                            # question instead of asking the user twice.
                            normalized_name=_contextual_name(label, context),
                            field_type=field_type,
                            confidence=0.6,
                            source=before.source,
                            label_bounding_box=before.bounding_box,
                            input_bounding_box=after.bounding_box,
                        )
                    )

            if found_any:
                consumed.add(index)

        return candidates


def _marker_requiredness(label: str) -> bool | None:
    """The three-state requiredness a group label's own marker declares.

    Returned as the tri-state `bool | None` the candidate carries: True for a
    positive finding, False for an explicit "optional", and None when the
    document said nothing — which must never be resolved to either.
    """
    state = detect_requiredness(label).state
    if state == REQUIRED:
        return True
    if state == OPTIONAL:
        return False
    return None
