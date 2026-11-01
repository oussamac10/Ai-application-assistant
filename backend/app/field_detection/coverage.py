"""What the document offered, versus what the extractor took.

`quality.py` scores the candidates an extractor produced. That is necessary and
not sufficient, and live testing showed exactly how it fails: on
`required_optional_validation_test_form.pdf` the local pass produced **5**
candidates for a two-page form carrying about thirty fields, and every one of
those five was perfect — good label, real input region, high confidence. The
weighted score came out at **0.83**, comfortably "good", and the document was
never escalated. The user then saw five questions instead of thirty.

The blind spot is structural: a score computed only from the output cannot see
what the output is missing. So coverage is measured against the *document*:

- **Label coverage.** Count the lines that look like a form asking for
  something — a trailing `*`, a trailing colon, an "(Optional)" marker, or a
  short line sitting directly above a rule or a blank run — and compare with
  how many candidates came back. Five candidates against thirty label lines is
  0.17, and no amount of per-candidate polish should hide that.
- **Selection-mark coverage.** Every drawn checkbox/radio on the page should
  end up inside some candidate's option list. Marks left unclaimed are options
  that leaked, or a group that was never formed.
- **Page coverage.** A page that produced nothing was almost certainly not
  read; a genuinely blank page is rare in a form someone uploaded.

These are counts of geometry and punctuation. Nothing here inspects meaning, so
nothing here can be wrong in an interesting way — which matters, because these
numbers decide whether a paid service is called
(`.agents/AGENTS.md`: AI never decides provider spending).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.field_detection.providers.base import (
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionToken,
)

# Fallback reason codes, reported when coverage rather than candidate quality
# is what triggered an escalation.
LOW_LABEL_COVERAGE = "low_label_coverage"
UNCLAIMED_SELECTION_MARKS = "unclaimed_selection_marks"
POOR_PAGE_COVERAGE = "poor_page_coverage"

# The glyphs `extraction.py` emits for a drawn checkbox / radio button. Matched
# rather than imported to keep this module free of extractor internals.
_MARK_GLYPHS = frozenset({"[_]", "(_)", "[x]", "(x)", "☐", "☑", "☒", "○", "●"})

# A line that is asking for something. Deliberately punctuation- and
# marker-based: no vocabulary, so it behaves the same in every language and on
# documents nobody anticipated.
_REQUIRED_MARK = re.compile(r"[*∗]\s*$")
_TRAILING_COLON = re.compile(r"[:：]\s*$")
_OPTIONALITY = re.compile(
    r"\((?:optional|facultatif|facultative|freiwillig|اختياري)\)\s*$",
    re.IGNORECASE,
)
# A label line is short. A paragraph of legal text is not a field, however many
# colons it contains.
_MAX_LABEL_WORDS = 12
_MIN_LABEL_CHARACTERS = 3

# Two tokens are on the same visual line when their vertical centres are within
# this fraction of the taller one's height.
_LINE_TOLERANCE = 0.6


@dataclass(frozen=True)
class DocumentCoverage:
    """How much of the document the extractor actually accounted for."""

    label_coverage: float
    mark_coverage: float
    page_coverage: float
    label_line_count: int
    selection_mark_count: int
    unclaimed_selection_marks: int
    pages_with_candidates: int
    page_count: int

    def weakest_signal(self) -> str | None:
        """The coverage failure worth reporting, or None if coverage is fine."""
        signals = (
            (self.page_coverage, POOR_PAGE_COVERAGE),
            (self.label_coverage, LOW_LABEL_COVERAGE),
            (self.mark_coverage, UNCLAIMED_SELECTION_MARKS),
        )
        worst_value, worst_code = min(signals, key=lambda pair: pair[0])
        return worst_code if worst_value < 1.0 else None


def _is_mark(token: DetectionToken) -> bool:
    return token.text.strip() in _MARK_GLYPHS


def _group_into_lines(tokens: list[DetectionToken]) -> list[list[DetectionToken]]:
    """Groups tokens into visual lines by vertical proximity.

    Direction-agnostic: tokens are only compared vertically, so an RTL page
    lines up exactly as an LTR one does.
    """
    lines: list[list[DetectionToken]] = []
    for token in sorted(tokens, key=lambda t: (t.bounding_box.y, t.bounding_box.x)):
        box = token.bounding_box
        centre = box.y + box.height / 2
        placed = False
        for line in lines:
            reference = line[0].bounding_box
            reference_centre = reference.y + reference.height / 2
            tolerance = max(reference.height, box.height) * _LINE_TOLERANCE
            if abs(centre - reference_centre) <= tolerance:
                line.append(token)
                placed = True
                break
        if not placed:
            lines.append([token])
    return lines


def _line_text(line: list[DetectionToken]) -> str:
    ordered = sorted(line, key=lambda t: t.bounding_box.x)
    return " ".join(t.text for t in ordered if not _is_mark(t)).strip()


def looks_like_a_label(text: str) -> bool:
    """Whether a line reads as a form asking for something.

    Punctuation and markers only — never vocabulary. "Nom de famille *" and
    "الاسم *" both qualify for the same reason.
    """
    stripped = text.strip()
    if len(stripped) < _MIN_LABEL_CHARACTERS:
        return False
    if len(stripped.split()) > _MAX_LABEL_WORDS:
        return False
    return bool(
        _REQUIRED_MARK.search(stripped)
        or _TRAILING_COLON.search(stripped)
        or _OPTIONALITY.search(stripped)
    )


def _count_label_lines(page: DetectionPageInput) -> int:
    return sum(
        1
        for line in _group_into_lines(list(page.tokens))
        if looks_like_a_label(_line_text(line))
    )


def _count_selection_marks(page: DetectionPageInput) -> int:
    return sum(1 for token in page.tokens if _is_mark(token))


def measure_coverage(
    document: DetectionDocumentInput,
    candidates: tuple[DetectedFieldCandidate, ...],
) -> DocumentCoverage:
    """Compares what the document offered with what came back.

    Every ratio is clamped to 1.0: an extractor that finds *more* than the
    label heuristic counted is doing well, not suspiciously well, and must not
    be able to score above a perfect coverage.
    """
    label_lines = sum(_count_label_lines(page) for page in document.pages)
    marks = sum(_count_selection_marks(page) for page in document.pages)

    claimed_options = sum(len(candidate.options) for candidate in candidates)
    unclaimed = max(0, marks - claimed_options)

    pages_with_candidates = len({candidate.page_number for candidate in candidates})
    # Measured against the pages that actually *offered* something — a label
    # line or a selection mark. A form's last page is routinely a signature
    # block, legal prose or continuation notes with no fields on it, and
    # counting it as a miss would escalate documents that were read
    # perfectly: the reference German rental contract is exactly this shape
    # (3 pages, fields on 2). Same conservative bias as `label_coverage`
    # above — no evidence of a gap is not evidence of a gap.
    pages_offering_content = sum(
        1
        for page in document.pages
        if _count_label_lines(page) > 0 or _count_selection_marks(page) > 0
    )
    # A form whose lines carry no punctuation at all gives this heuristic
    # nothing to work with. Reporting 1.0 is the honest answer — "no evidence
    # of a gap" — rather than 0.0, which would escalate every such document.
    # All three ratios follow the same rule, including page coverage: if no
    # page offered a label line or a mark, there is nothing to have missed.
    label_coverage = (
        1.0 if label_lines == 0 else min(1.0, len(candidates) / label_lines)
    )
    mark_coverage = 1.0 if marks == 0 else min(1.0, claimed_options / marks)
    page_coverage = (
        1.0
        if pages_offering_content == 0
        else min(1.0, pages_with_candidates / pages_offering_content)
    )
    page_count = pages_offering_content or document.page_count or len(document.pages)

    return DocumentCoverage(
        label_coverage=round(label_coverage, 4),
        mark_coverage=round(mark_coverage, 4),
        page_coverage=round(page_coverage, 4),
        label_line_count=label_lines,
        selection_mark_count=marks,
        unclaimed_selection_marks=unclaimed,
        pages_with_candidates=pages_with_candidates,
        page_count=page_count,
    )
