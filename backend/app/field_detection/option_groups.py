"""Turns a row of selection marks into one choice question.

The existing choice-group pass (`LocalFieldDetectionProvider._detect_choice_groups`)
only recognises a group when a heading sits immediately above the options. Real
forms frequently omit it — a French application form puts

    [_] Femme  [_] Homme  [_] Non-binaire  [_] Je préfère ne pas répondre

directly under an unrelated line, and the declaration row under a prose
sentence. Those rows fell through to the generic passes, so every *option*
became its own free-text question ("Non-binaire", "Je préfère ne pas répondre",
"J'accepte la déclaration") and the actual question — "Gender" — never existed.

This pass runs *after* the heading-based one, on the rows it did not consume, so
existing German behaviour is untouched and only the previously-missed rows are
added.

Naming a group is the hard part, and inventing a label is worse than admitting
ignorance. Three sources are tried in descending order of confidence:

1. **A recognised option set.** `{femme, homme, non-binaire, ...}` is a gender
   question in any language; the option values themselves are the evidence, and
   no geometry can contradict them.
2. **The nearest section heading above**, with its numbering stripped
   ("2. Situation professionnelle actuelle" -> "Situation professionnelle
   actuelle"). Weaker, because a heading can cover several groups.
3. **A neutral deterministic label**, flagged for admin review. Used when
   neither of the above applies — the group still becomes one question rather
   than N spurious text fields, which is the outcome that matters.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.field_detection.classification import marker_type
from app.field_detection.geometry import union_bounding_box
from app.field_detection.labeling import LinePhrase
from app.field_detection.providers.base import BoundingBox, DetectionToken

logger = logging.getLogger(__name__)

# A choice option is a short phrase. Anything longer is a statement, and a
# group of statements is not a choice list.
_MAX_OPTION_WORDS = 8

# Leading enumeration on a section heading: "2.", "2)", "§ 2", "II.".
# "2.", "2)", "II.", and the German "§ 3" form, which has no trailing
# punctuation of its own.
_HEADING_NUMBER = re.compile(r"^\s*(?:§\s*[0-9]+\s+|[0-9IVXivx]+\s*[.)\-–]\s*)")


@dataclass(frozen=True)
class OptionGroup:
    """One detected group, ready to become a single choice question."""

    label: str
    options: tuple[str, ...]
    field_type: str
    page_number: int
    bounding_box: BoundingBox
    line_indices: tuple[int, ...]
    label_source: str
    needs_review: bool
    confidence: float


# ---------------------------------------------------------------------------
# Recognised option sets
# ---------------------------------------------------------------------------
#
# Matching is on *option* text, so a set identifies a question regardless of
# what (if anything) the form calls it. Each entry lists enough distinctive
# members that an accidental match is implausible, in every UI language the
# product supports. `exclusive` decides single_choice vs multiple_choice: you
# have one gender, but you may speak several languages.


@dataclass(frozen=True)
class _OptionSet:
    key: str
    label: str
    exclusive: bool
    members: frozenset[str]
    # How many distinct members must appear before the set is considered
    # matched. Two is enough for a distinctive vocabulary.
    minimum_matches: int = 2


_OPTION_SETS: tuple[_OptionSet, ...] = (
    _OptionSet(
        key="gender",
        label="Gender",
        exclusive=True,
        members=frozenset(
            {
                "male",
                "female",
                "non-binary",
                "nonbinary",
                "non binary",
                "prefer not to answer",
                "prefer not to say",
                "mann",
                "frau",
                "männlich",
                "weiblich",
                "divers",
                "keine angabe",
                "möchte ich nicht angeben",
                "homme",
                "femme",
                "non-binaire",
                "non binaire",
                "je préfère ne pas répondre",
                "préfère ne pas répondre",
                "ذكر",
                "أنثى",
                "غير ثنائي",
                "أفضل عدم الإجابة",
            }
        ),
    ),
    _OptionSet(
        key="employment_status",
        label="Employment status",
        exclusive=True,
        members=frozenset(
            {
                "employed",
                "self-employed",
                "self employed",
                "student",
                "job seeker",
                "jobseeker",
                "unemployed",
                "retired",
                "angestellt",
                "selbständig",
                "selbstständig",
                "studentin",
                "arbeitssuchend",
                "arbeitslos",
                "rentner",
                "salarié",
                "salarié(e)",
                "salariée",
                "indépendant",
                "indépendant(e)",
                "indépendante",
                "étudiant",
                "étudiant(e)",
                "étudiante",
                "demandeur d'emploi",
                "retraité",
                "retraité(e)",
                "موظف",
                "عمل حر",
                "طالب",
                "باحث عن عمل",
                "متقاعد",
            }
        ),
    ),
    _OptionSet(
        key="languages",
        label="Languages",
        exclusive=False,
        members=frozenset(
            {
                "arabic",
                "german",
                "english",
                "french",
                "spanish",
                "turkish",
                "arabisch",
                "deutsch",
                "englisch",
                "französisch",
                "arabe",
                "allemand",
                "anglais",
                "français",
                "العربية",
                "الألمانية",
                "الإنجليزية",
                "الفرنسية",
            }
        ),
    ),
    _OptionSet(
        key="contact_method",
        label="Preferred contact method",
        exclusive=False,
        members=frozenset(
            {
                "email",
                "e-mail",
                "phone",
                "telephone",
                "post",
                "postal mail",
                "letter",
                "sms",
                "telefon",
                "brief",
                "téléphone",
                "courrier postal",
                "courrier",
                "البريد الإلكتروني",
                "الهاتف",
                "البريد",
            }
        ),
    ),
    _OptionSet(
        key="marital_status",
        label="Marital status",
        exclusive=True,
        members=frozenset(
            {
                "single",
                "married",
                "divorced",
                "widowed",
                "ledig",
                "verheiratet",
                "geschieden",
                "verwitwet",
                "célibataire",
                "marié",
                "marié(e)",
                "divorcé",
                "divorcé(e)",
                "veuf",
                "veuve",
                "أعزب",
                "متزوج",
                "مطلق",
                "أرمل",
            }
        ),
    ),
    _OptionSet(
        key="yes_no",
        label="Yes or no",
        exclusive=True,
        members=frozenset({"yes", "no", "ja", "nein", "oui", "non", "نعم", "لا"}),
    ),
)

# Options that start like a declaration ("I accept …", "J'accepte …"). A row of
# these is a consent group, which is independently selectable.
_DECLARATION_PREFIXES = (
    "i accept",
    "i agree",
    "i confirm",
    "i certify",
    "i declare",
    "ich akzeptiere",
    "ich stimme",
    "ich bestätige",
    "ich erkläre",
    "j'accepte",
    "je certifie",
    "je confirme",
    "je déclare",
    "أوافق",
    "أقر",
)

_DECLARATION_LABEL = "Declarations"

# Used when nothing else identifies the group. Deliberately neutral: it says
# what the thing is without pretending to know what it asks.
_NEUTRAL_LABEL = "Selection group"


def _normalize_option(text: str) -> str:
    return " ".join(text.strip().lower().rstrip(".;,").split())


def match_option_set(options: tuple[str, ...]) -> _OptionSet | None:
    """The recognised set these options belong to, if any.

    Requires `minimum_matches` distinct members *and* that matches form a
    majority of the row, so one coincidental word cannot rename a group.
    """
    normalized = {_normalize_option(option) for option in options}
    best: _OptionSet | None = None
    best_hits = 0
    for option_set in _OPTION_SETS:
        hits = len(normalized & option_set.members)
        if hits >= option_set.minimum_matches and hits * 2 >= len(normalized):
            if hits > best_hits:
                best, best_hits = option_set, hits
    return best


def independent_boolean_options(
    options: tuple[str, ...],
) -> tuple[tuple[str, str], ...] | None:
    """Splits a group whose *options* carry their own requiredness markers.

    Returns `((label, requiredness), ...)`, or None when the group is a normal
    choice question.

    The French test form ends with:

        [_] Je certifie que les informations sont exactes *
        [_] J'accepte le traitement des donnees de test *
        [_] Je souhaite recevoir des nouvelles (Optional)

    Grouped as one `multiple_choice`, that becomes "tick any of these" — and
    the two mandatory consents silently stop being mandatory, which is the one
    thing a declaration block exists to enforce. They are not options of a
    question; they are three independent yes/no answers that happen to sit
    together.

    The trigger is structural, not vocabulary: **an option carrying its own
    requiredness marker cannot be an option**, because a choice question's
    requiredness belongs to the question, not to individual answers. So this
    fires on any such block in any language, while "Documents joints" — six
    unmarked checkboxes — stays a single multiple_choice.
    """
    from app.field_detection.requiredness import (
        UNKNOWN,
        detect_requiredness,
        strip_requiredness_markers,
    )

    resolved = [
        (strip_requiredness_markers(option), detect_requiredness(option).state)
        for option in options
    ]
    if not any(state != UNKNOWN for _label, state in resolved):
        return None
    return tuple(resolved)


def _is_declaration_group(options: tuple[str, ...]) -> bool:
    normalized = [_normalize_option(option) for option in options]
    hits = sum(
        1
        for option in normalized
        if any(option.startswith(prefix) for prefix in _DECLARATION_PREFIXES)
    )
    return hits >= 1 and hits * 2 >= len(normalized)


def strip_heading_number(text: str) -> str:
    """ "2. Situation professionnelle" -> "Situation professionnelle"."""
    return _HEADING_NUMBER.sub("", text).strip().rstrip(":").strip()


# ---------------------------------------------------------------------------
# Row parsing
# ---------------------------------------------------------------------------


def _split_segment_at_markers(
    segment: LinePhrase,
) -> list[tuple[str, str]] | None:
    """Splits one segment into (marker_kind, label) pairs, one per marker.

    Segmentation is gap-based, so how many options land in a segment depends on
    how tightly the form spaces them. On the French test form the professional-
    status row segments as

        "(_) Salarie(e)" | "(_) Independant(e)" | "(_) Etudiant(e) (_) Demandeur d'emploi"

    because the gap before the fourth marker is narrower than the others.
    Requiring exactly one marker per segment rejected that entire row, so the
    group was never formed and all four options leaked as separate text
    questions — the reported "Statut professionnel" failure.

    A marker is an unambiguous structural boundary: everything from one marker
    up to the next is that marker's label. Reading it that way makes the result
    independent of the spacing the document happened to use.
    """
    tokens = sorted(segment.tokens, key=lambda t: t.bounding_box.x)
    marker_positions = [
        index for index, token in enumerate(tokens) if marker_type(token.text)
    ]
    if not marker_positions:
        return None

    options: list[tuple[str, str]] = []
    for order, start in enumerate(marker_positions):
        kind = marker_type(tokens[start].text)
        if kind is None:
            return None
        end = (
            marker_positions[order + 1]
            if order + 1 < len(marker_positions)
            else len(tokens)
        )
        label = " ".join(t.text for t in tokens[start + 1 : end]).strip()
        if not label:
            return None
        if len(label.split()) > _MAX_OPTION_WORDS or label.rstrip().endswith("."):
            # A sentence is a statement, not an option.
            return None
        options.append((kind, label))
    return options


def _parse_option_row(segments: list[LinePhrase]) -> list[tuple[str, str]] | None:
    """Parses one physical line as a row of marker+label options.

    Returns None unless *every* segment on the line carries at least one marker
    with a short label after it — a line mixing options with other content is
    not an option row, and treating it as one would swallow a real field.
    """
    options: list[tuple[str, str]] = []
    for segment in segments:
        parsed = _split_segment_at_markers(segment)
        if parsed is None:
            return None
        options.extend(parsed)
    return options or None


def _row_tokens(segments: list[LinePhrase]) -> list[DetectionToken]:
    return [token for segment in segments for token in segment.tokens]


def detect_option_groups(
    page_number: int,
    line_groups: list[list[LinePhrase]],
    consumed: set[int],
    heading_for_line: dict[int, str],
) -> list[OptionGroup]:
    """Finds option rows the earlier passes left behind and groups each into
    one question.

    Each row becomes its own group. Merging consecutive rows was considered and
    rejected: a French form places "Français / Allemand / Anglais / Arabe" and
    "E-mail / Téléphone / Courrier postal" on adjacent rows with identical
    spacing and the same heading, so any geometric merge rule would join two
    unrelated questions. One question per row is occasionally too granular (a
    long wrapped checklist splits in two) but is never *wrong* in the way a
    merge would be.
    """
    groups: list[OptionGroup] = []

    for index, segments in enumerate(line_groups):
        if index in consumed:
            continue
        parsed = _parse_option_row(segments)
        if parsed is None or len(parsed) < 2:
            continue

        options = tuple(label for _, label in parsed)
        marker_kinds = {kind for kind, _ in parsed}

        label, label_source, needs_review, exclusive = _resolve_group_label(
            options, heading_for_line.get(index)
        )

        # Marker geometry wins when it is unambiguous: parentheses are radio
        # buttons (pick one), brackets are checkboxes (pick any). Only when
        # the glyphs cannot decide does the recognised set's own exclusivity
        # apply.
        if marker_kinds == {"radio"}:
            field_type = "radio"
        elif marker_kinds == {"checkbox"}:
            field_type = "radio" if exclusive else "multiple_choice"
        else:
            # Mixed glyphs are contradictory evidence; skip rather than guess.
            continue

        box = union_bounding_box([t.bounding_box for t in _row_tokens(segments)])
        groups.append(
            OptionGroup(
                label=label,
                options=options,
                field_type=field_type,
                page_number=page_number,
                bounding_box=box,
                line_indices=(index,),
                label_source=label_source,
                needs_review=needs_review,
                # A named group is solid evidence; a neutral one is a
                # structural guess and routes to review via the normal
                # confidence thresholds.
                confidence=0.55 if needs_review else 0.85,
            )
        )
        consumed.add(index)

    return groups


def _resolve_group_label(
    options: tuple[str, ...], heading: str | None
) -> tuple[str, str, bool, bool]:
    """Returns (label, source, needs_review, exclusive)."""
    option_set = match_option_set(options)
    if option_set is not None:
        return option_set.label, "option_set", False, option_set.exclusive

    if _is_declaration_group(options):
        return _DECLARATION_LABEL, "declaration", False, False

    if heading:
        cleaned = strip_heading_number(heading)
        if cleaned:
            return cleaned, "heading", False, False

    # Nothing identifies it. One question with a neutral name beats N spurious
    # text questions, but an admin should look at it.
    return _NEUTRAL_LABEL, "neutral", True, False
