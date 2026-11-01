"""Automatic detection of the language a document is actually written in.

The pipeline could never answer this before. `question_bridge` assumed
`_DEFAULT_SOURCE_LANGUAGE` ("en") for every document, which is why a German
contract's labels were stored as English and — because the assumption matched
an English interface — were never translated at all. Azure Translator's own
`detectedLanguage` was meant to close the gap, but it only arrives *with* a
translation, so a document needing no translation still had no answer, and a
provider failure silently replaced a real detection with the assumption.

So detection is its own capability, run once per document straight after text
extraction or OCR, persisted, and consulted before anything language-sensitive
happens — geometry grouping, question generation, translation.

`LocalDocumentLanguageDetector` is deterministic and dependency-free, which
matters more here than breadth:

- **Script first.** Arabic, Hebrew, Greek, Cyrillic and CJK are decided by
  Unicode block. A document in Arabic script is Arabic regardless of what any
  word-frequency model thinks, and this is the branch RTL grouping depends on.
- **Function words for Latin script.** Short, extremely common words ("der",
  "und", "the", "les", "een") separate en/de/fr/es/it/nl/pt reliably on form
  text, which is mostly labels rather than prose. Diacritics break ties.
- **`und` when unsure.** A form with four words in it genuinely has no
  detectable language, and `.agents/AGENTS.md` forbids inventing
  information. Guessing "en" is what caused the original bug.

Confidence is a real ratio (winning score over total score), never an invented
number — the domain rules allow storing a confidence only when it comes from a
provider with documented semantics, and "share of matched function words" is
exactly that.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# ISO 639-1 plus the ISO 639-2 "undetermined" code, which is the honest answer
# for a document with too little text.
UNDETERMINED = "und"

DETECTION_VERSION = "1"

# Below this many usable words, any answer is noise. A form whose only text is
# "Name" tells us nothing.
_MIN_WORDS = 8

# Below this share of the total score the winner is not distinct enough from
# the runner-up to be trusted.
_MIN_CONFIDENCE = 0.34

# Unicode script ranges that identify a language (or narrow it enough) on their
# own. Checked before any word statistics.
_SCRIPT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("ar", 0x0600, 0x06FF),  # Arabic
    ("ar", 0x0750, 0x077F),  # Arabic Supplement
    ("ar", 0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    ("ar", 0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    ("he", 0x0590, 0x05FF),  # Hebrew
    ("el", 0x0370, 0x03FF),  # Greek
    ("ru", 0x0400, 0x04FF),  # Cyrillic
    ("zh", 0x4E00, 0x9FFF),  # CJK Unified Ideographs
    ("ja", 0x3040, 0x30FF),  # Hiragana + Katakana
    ("ko", 0xAC00, 0xD7AF),  # Hangul Syllables
)

# Right-to-left languages. Consumed by field-detection geometry grouping, which
# must associate a blank with the label on its *right* for these.
RTL_LANGUAGES = frozenset({"ar", "he", "fa", "ur"})

# Very common function words per language. Deliberately short lists of words
# that are frequent in ordinary text and rare as form labels, so they identify
# a language without being confused by domain vocabulary.
_FUNCTION_WORDS: dict[str, frozenset[str]] = {
    "de": frozenset(
        """der die das und ist von den dem des ein eine einen einem einer nicht
        mit sich auch auf für bei aus dass wird werden sind oder wenn zum zur
        im am als nach über durch vom bis kann sowie diese dieser""".split()
    ),
    "en": frozenset(
        """the and is of to in that it for on with as are was be this you your
        have has not or if from by an at which will can any all please
        other than then""".split()
    ),
    "fr": frozenset(
        """le la les des une dans est pour que qui pas vous nous avec sur par
        plus sont ont été cette ces aux votre notre mais ou son ses au du
        être avoir""".split()
    ),
    "es": frozenset(
        """el la los las una del que por con para como más pero sus este esta
        son han está sobre entre cuando muy todo entonces también sin
        entrada""".split()
    ),
    "it": frozenset(
        """il lo la gli le dei delle una che per con non sono come più questo
        questa nel nella alla dal dalla anche quando sua suo essere""".split()
    ),
    "nl": frozenset(
        """de het een van en is dat op te zijn met voor niet aan door bij uit
        naar wordt worden deze dit maar ook als om over""".split()
    ),
    "pt": frozenset(
        """de da do os as um uma que para com não por mais como mas seu sua ao
        dos das pelo pela quando muito também sem""".split()
    ),
}

# Characters that point at *one* Latin-script language. Deliberately only the
# discriminative ones: é/è/à are shared by French, Spanish, Italian and
# Portuguese, so counting them added the same bonus to all four and decided
# nothing while inflating the denominator. ß, ñ, œ and ã do discriminate.
_DIACRITIC_HINTS: dict[str, str] = {
    "de": "äöüßÄÖÜ",
    "fr": "çœëïÿÇŒËÏŸ",
    "es": "ñ¿¡Ñ",
    "it": "",
    "pt": "ãõÃÕ",
    "nl": "ĳĲ",
}

# How much one function-word match is worth, by how many languages claim the
# word. "de" appears in four of the lists and says almost nothing; "vous"
# appears in one and is decisive. Without this, French text scored barely
# above Dutch and Portuguese on a form whose vocabulary is mostly shared
# short words, and the document came back `und`.
_WORD_WEIGHTS: dict[str, float] = {}
for _vocabulary in _FUNCTION_WORDS.values():
    for _word in _vocabulary:
        _WORD_WEIGHTS[_word] = _WORD_WEIGHTS.get(_word, 0.0) + 1.0
_WORD_WEIGHTS = {word: 1.0 / count for word, count in _WORD_WEIGHTS.items()}

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


@dataclass(frozen=True)
class DetectedLanguage:
    """The outcome of one detection. `language` is an ISO 639-1 code, or
    `und` when nothing could be determined."""

    language: str
    confidence: float
    provider: str
    version: str = DETECTION_VERSION

    @property
    def is_determined(self) -> bool:
        return self.language != UNDETERMINED

    @property
    def is_rtl(self) -> bool:
        return self.language in RTL_LANGUAGES


@runtime_checkable
class DocumentLanguageDetector(Protocol):
    provider_name: str

    async def detect(self, text: str) -> DetectedLanguage: ...


def _script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for character in text:
        code = ord(character)
        for language, start, end in _SCRIPT_RANGES:
            if start <= code <= end:
                counts[language] = counts.get(language, 0) + 1
                break
    return counts


def _latin_letter_count(text: str) -> int:
    return sum(
        1
        for character in text
        if character.isalpha() and "LATIN" in unicodedata.name(character, "")
    )


class LocalDocumentLanguageDetector:
    """Deterministic, offline, no new dependency. See the module docstring."""

    provider_name = "local"

    async def detect(self, text: str) -> DetectedLanguage:
        return self.detect_sync(text)

    def detect_sync(self, text: str) -> DetectedLanguage:
        """Synchronous twin — detection is pure CPU work, and the extraction
        pipeline that calls it is synchronous."""
        if not text or not text.strip():
            return DetectedLanguage(UNDETERMINED, 0.0, self.provider_name)

        # 1. Script. A non-Latin script is decisive: no amount of word
        #    statistics should be able to call Arabic text English.
        scripts = _script_counts(text)
        latin = _latin_letter_count(text)
        if scripts:
            language, count = max(scripts.items(), key=lambda item: item[1])
            total = count + latin
            if total > 0 and count / total >= 0.5:
                # Confidence is the script's share of all letters — a real
                # measured ratio, not an invented score.
                return DetectedLanguage(
                    language, round(count / total, 4), self.provider_name
                )

        words = [word.lower() for word in _WORD_RE.findall(text)]
        if len(words) < _MIN_WORDS:
            logger.info(
                "Language detection: too little text (words=%d, minimum=%d) -> und",
                len(words),
                _MIN_WORDS,
            )
            return DetectedLanguage(UNDETERMINED, 0.0, self.provider_name)

        # 2. Function-word frequency across the Latin-script candidates.
        scores: dict[str, float] = {}
        for language, vocabulary in _FUNCTION_WORDS.items():
            scores[language] = sum(
                _WORD_WEIGHTS.get(word, 1.0) for word in words if word in vocabulary
            )

        # 3. Diacritics break near-ties only. Weighted below a function-word
        #    match so a single stray character cannot decide a document.
        for language, characters in _DIACRITIC_HINTS.items():
            hits = sum(1 for character in text if character in characters)
            if hits:
                scores[language] = scores.get(language, 0.0) + min(hits, 10) * 0.5

        total_score = sum(scores.values())
        if total_score <= 0:
            logger.info("Language detection: no function-word evidence -> und")
            return DetectedLanguage(UNDETERMINED, 0.0, self.provider_name)

        # Deterministic ordering: highest score, then alphabetical, so an exact
        # tie always resolves the same way rather than by dict iteration order.
        language = min(
            sorted(scores), key=lambda candidate: (-scores[candidate], candidate)
        )
        confidence = scores[language] / total_score

        if confidence < _MIN_CONFIDENCE:
            logger.info(
                "Language detection: best candidate confidence %.2f below "
                "threshold %.2f -> und",
                confidence,
                _MIN_CONFIDENCE,
            )
            return DetectedLanguage(UNDETERMINED, round(confidence, 4), "local")

        return DetectedLanguage(language, round(confidence, 4), self.provider_name)


class MockDocumentLanguageDetector:
    """Returns a fixed answer. Tests that care about *what happens with* a
    language must not depend on the detector's accuracy."""

    provider_name = "mock"

    def __init__(self, language: str = "en", confidence: float = 1.0) -> None:
        self._language = language
        self._confidence = confidence
        self.calls = 0

    async def detect(self, text: str) -> DetectedLanguage:
        self.calls += 1
        return DetectedLanguage(self._language, self._confidence, self.provider_name)

    def detect_sync(self, text: str) -> DetectedLanguage:
        self.calls += 1
        return DetectedLanguage(self._language, self._confidence, self.provider_name)
