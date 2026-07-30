"""How good is a local extraction, measured deterministically?

Hybrid routing needs one honest answer to "did the local pass actually
understand this document?", and it has to be plain code. `docs/claude/
domain-rules.md` says a confidence value may only be stored when it comes from
a provider with documented semantics, and forbids asking a model to invent one
— so this is not a confidence score about the *document*. It is an arithmetic
summary of what the local pass produced, computed from the candidates
themselves, with no model involved and no network call.

That matters for cost as much as for correctness: the escalation decision
decides whether a paid service is called, and `domain-rules.md` is explicit
that AI never decides provider spending.

Four signals, each answering a different failure mode seen in live testing:

- **Field count.** A form that yields one or two candidates was not read. The
  Arabic form that collapsed 27 candidates into 2 is the reference case.
- **Label quality.** A candidate whose label is a placeholder, a bare number or
  a single stray character is a box the pass found without understanding.
  Detection can find geometry and still not find questions.
- **Input evidence.** A candidate with somewhere to write is a real field; a
  page of labels with no input regions usually means the layout pass missed the
  structure.
- **Confidence.** The local provider's own per-candidate confidence, which has
  documented semantics within that provider.

They are combined by weighted average rather than by an all-must-pass rule: a
document can be poor on one signal and unambiguously fine overall (a short
form legitimately has few fields), and any single hard gate would escalate it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.field_detection.providers.base import DetectedFieldCandidate

# Below this many candidates a document is treated as barely read at all, and
# the count signal saturates to zero rather than scaling smoothly — the
# difference between 1 and 2 candidates is not meaningful.
_MINIMUM_USEFUL_FIELDS = 3

# At or above this many candidates the count signal is satisfied. Chosen from
# the reference forms: the German rental contract yields 21, the French
# employment form 37, and a genuinely short form that yields 8 should not be
# escalated for its length alone.
_HEALTHY_FIELD_COUNT = 8

# A label that is only digits, punctuation, or one or two characters carries no
# question. Deliberately narrow: a real label in any script passes.
_PLACEHOLDER_LABEL = re.compile(r"^[\W\d_]*$", re.UNICODE)
_MIN_LABEL_CHARACTERS = 3

# Weights sum to 1.0. Label quality dominates because it is the signal that
# distinguishes "found boxes" from "found questions", which is exactly what a
# hosted layout service is being paid to do better.
_WEIGHT_FIELD_COUNT = 0.25
_WEIGHT_LABEL_QUALITY = 0.40
_WEIGHT_INPUT_EVIDENCE = 0.20
_WEIGHT_CONFIDENCE = 0.15


@dataclass(frozen=True)
class ExtractionQuality:
    """A local result's measured quality, plus the parts it was built from.

    Every component is reported so a routing decision can be explained from a
    log line without re-running anything — and so an operator can see *which*
    signal triggered an escalation rather than only that one did.
    """

    score: float
    field_count: int
    label_quality: float
    input_evidence: float
    mean_confidence: float

    def weakest_signal(self) -> str:
        """The component that contributed least, as a stable reason code."""
        components = {
            "low_field_count": _field_count_signal(self.field_count),
            "low_label_quality": self.label_quality,
            "low_input_evidence": self.input_evidence,
            "low_confidence": self.mean_confidence,
        }
        return min(components, key=lambda name: components[name])


def _field_count_signal(count: int) -> float:
    if count <= _MINIMUM_USEFUL_FIELDS:
        return 0.0
    if count >= _HEALTHY_FIELD_COUNT:
        return 1.0
    span = _HEALTHY_FIELD_COUNT - _MINIMUM_USEFUL_FIELDS
    return (count - _MINIMUM_USEFUL_FIELDS) / span


def is_meaningful_label(label: str | None) -> bool:
    """Whether a label reads as a question rather than as leftover geometry."""
    if not label:
        return False
    stripped = label.strip()
    if len(stripped) < _MIN_LABEL_CHARACTERS:
        return False
    return not _PLACEHOLDER_LABEL.match(stripped)


def score_extraction(
    candidates: tuple[DetectedFieldCandidate, ...],
) -> ExtractionQuality:
    """Measures one provider's output. Pure arithmetic, no I/O, no model."""
    count = len(candidates)
    if count == 0:
        return ExtractionQuality(0.0, 0, 0.0, 0.0, 0.0)

    meaningful = sum(1 for c in candidates if is_meaningful_label(c.label))
    with_input = sum(
        1 for c in candidates if c.input_bounding_box is not None or c.options
    )
    confidence = sum(c.confidence for c in candidates) / count

    label_quality = meaningful / count
    input_evidence = with_input / count

    score = (
        _WEIGHT_FIELD_COUNT * _field_count_signal(count)
        + _WEIGHT_LABEL_QUALITY * label_quality
        + _WEIGHT_INPUT_EVIDENCE * input_evidence
        + _WEIGHT_CONFIDENCE * confidence
    )

    return ExtractionQuality(
        score=round(score, 4),
        field_count=count,
        label_quality=round(label_quality, 4),
        input_evidence=round(input_evidence, 4),
        mean_confidence=round(confidence, 4),
    )
