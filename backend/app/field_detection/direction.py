"""Text-direction awareness for geometry and label assembly.

Every geometric heuristic in `geometry.py` and `providers/local.py` was written
for left-to-right text, and encodes that assumption twice:

- **Reading order.** Tokens are sorted by ascending x and joined with spaces.
  For Arabic that reverses the sentence: the form's title
  `نموذج طلب دعم سكني` comes back as `سكني دعم طلب نموذج`. The characters are
  intact — this is not mojibake — but the word order is backwards, which makes
  every label wrong and every keyword match unreliable.
- **Label/value adjacency.** A blank is assumed to follow its label to the
  *right*. In an RTL form the value area sits to the **left** of its label.

Both are fixed by ordering tokens by *reading position* rather than by x, so
the existing passes keep working unchanged in either direction.

Direction comes from the document's detected language
(`app/language/detector.py`), never from guessing per line: a mixed line
containing an English word inside an Arabic label must still read
right-to-left.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from app.language.detector import RTL_LANGUAGES


class _HasBoundingBox(Protocol):
    @property
    def bounding_box(self) -> object: ...


def is_rtl_language(language: str | None) -> bool:
    """Whether text in `language` reads right-to-left."""
    if not language:
        return False
    # Tolerate a regional tag ("ar-EG").
    return language.split("-")[0].lower() in RTL_LANGUAGES


def reading_sort_key(rtl: bool) -> Callable[[object], float]:
    """A sort key placing tokens in reading order.

    For RTL that is descending x, so the *rightmost* token comes first —
    which is exactly what makes `" ".join(...)` produce the correct sentence.
    """

    def key(token: object) -> float:
        box = getattr(token, "bounding_box", None)
        x = float(getattr(box, "x", 0.0))
        return -x if rtl else x

    return key


def order_for_reading(tokens: Iterable[object], rtl: bool) -> list[object]:
    return sorted(tokens, key=reading_sort_key(rtl))


def join_tokens(tokens: Sequence[object], rtl: bool) -> str:
    """Joins token text in reading order.

    The token strings themselves are never touched: no reversal, no
    normalization, no bidi rewriting. Only their *order* is direction-aware,
    so Arabic characters and combining marks survive byte-for-byte.
    """
    ordered = order_for_reading(tokens, rtl)
    return " ".join(str(getattr(token, "text", "")) for token in ordered).strip()


def value_side_is_left(rtl: bool) -> bool:
    """Which side of a label its input area occupies.

    LTR forms put the blank after the label (to its right); RTL forms put it
    before (to its left). Callers use this instead of hard-coding "the next
    token to the right is the value".
    """
    return rtl
