"""Builds the text sample language detection actually runs on.

Form text is unusually hostile to language detection. A large share of it is
identifiers — IBANs, dates, amounts, emails, reference numbers — which carry no
language at all but plenty of Latin letters, so feeding raw extracted text in
biases every document toward whichever Latin language the leftovers resemble.

So the sample is filtered rather than truncated:

- identifier-only lines are dropped, reusing the same deterministic rules the
  translation pipeline uses to decide what must never be translated
  (`app/translation/protected.py`) — one definition of "this is not language",
  not two that can drift apart;
- lines with no letters go;
- very short fragments are kept only in aggregate, because a form is mostly
  short labels and dropping them all would leave nothing.

The result is capped at `MAX_SAMPLE_CHARACTERS`. The cap is a cost bound, not a
quality one: detection accuracy plateaus long before it, and an unbounded
sample would let a 200-page scan dominate a request.
"""

from __future__ import annotations

import re

from app.translation.protected import is_protected

# Generous enough that a normal form contributes all of its prose, small enough
# that a huge scanned document cannot blow up memory or latency.
MAX_SAMPLE_CHARACTERS = 5000

_WHITESPACE = re.compile(r"[ \t]+")


def _clean_line(line: str) -> str:
    return _WHITESPACE.sub(" ", line).strip()


def build_language_sample(
    *sources: str, max_characters: int = MAX_SAMPLE_CHARACTERS
) -> str:
    """Combines text `sources` (page text, OCR output, detected labels) into
    one filtered sample.

    Sources are consumed in order, so a caller can put the most
    language-bearing text first — headings and paragraphs before isolated
    labels — and still get a useful sample when the cap truncates.
    """
    kept: list[str] = []
    length = 0
    seen: set[str] = set()

    for source in sources:
        if not source:
            continue
        for raw_line in source.splitlines():
            line = _clean_line(raw_line)
            if not line or line in seen:
                continue

            # No letters at all: page numbers, rule characters, dotted leaders.
            if not any(character.isalpha() for character in line):
                continue

            # Whole-line identifiers carry no language. Same deterministic
            # rules the translation pipeline uses, so the two cannot drift.
            if is_protected(line):
                continue

            seen.add(line)
            kept.append(line)
            length += len(line) + 1
            if length >= max_characters:
                return "\n".join(kept)[:max_characters]

    return "\n".join(kept)[:max_characters]


def has_enough_text(sample: str, minimum_words: int = 8) -> bool:
    """Whether a sample is worth running detection on at all. Kept next to the
    builder so callers do not each invent their own threshold."""
    return len(re.findall(r"[^\W\d_]+", sample, re.UNICODE)) >= minimum_words
