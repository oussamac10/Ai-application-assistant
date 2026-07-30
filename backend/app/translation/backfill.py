"""Fills in the languages question preparation deliberately deferred.

Phase 15 translates only the user-interface language during
`prepare-questions`, because that is the only text a user can see while
answering. Every other supported language gets source-text placeholder rows so
`FormService.publish_version` is satisfied and the session starts immediately
(see `question_bridge._deferred_languages`).

This module replaces those placeholders when the text is actually needed —
review or export — and is idempotent: a row that already differs from its
source text is left alone, so calling it twice costs nothing and it can never
overwrite a real translation with a fresh guess.

It writes to a *published* version's translation rows. That is intentional and
narrow: publishing freezes a version's **structure** (its fields, keys, types
and option values, all of which answers and exports depend on), not the
display text of a language it was published without. No field, option or value
is added, removed or changed here — only a placeholder label is replaced by its
translation.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.forms.models import FormVersion
from app.translation.base import TranslationProvider
from app.translation.service import TranslationStats, translate_texts

logger = logging.getLogger(__name__)


def _placeholder_rows(
    version: FormVersion, language: str
) -> tuple[list[object], list[str]]:
    """Rows still holding source text for `language`, plus the distinct source
    strings they need translated.

    A row is a placeholder when its label is byte-identical to the source
    language's label. That is a deliberate over-approximation in one direction
    only: a genuine translation that happens to equal its source (a proper
    noun, "IBAN") is harmless to re-translate, whereas treating a real
    placeholder as done would leave the user looking at the wrong language.
    """
    rows: list[object] = []
    texts: list[str] = []
    source_language = version.source_language

    for field in version.fields:
        source_label = next(
            (t.label for t in field.translations if t.language == source_language),
            None,
        )
        for translation in field.translations:
            if translation.language == language and translation.label == source_label:
                rows.append(translation)
                texts.append(translation.label)

        for option in field.options:
            source_option = next(
                (t.label for t in option.translations if t.language == source_language),
                None,
            )
            for option_translation in option.translations:
                if (
                    option_translation.language == language
                    and option_translation.label == source_option
                ):
                    rows.append(option_translation)
                    texts.append(option_translation.label)

    return rows, list(dict.fromkeys(texts))


async def backfill_language(
    db: Session,
    version: FormVersion,
    language: str,
    provider: TranslationProvider,
    fallback_provider: TranslationProvider | None = None,
) -> TranslationStats:
    """Translates `version`'s placeholder rows for `language` in place.

    Safe to call unconditionally: with nothing to do it makes no provider call
    and returns zeroed stats.
    """
    stats = TranslationStats()

    if language == version.source_language:
        return stats

    rows, texts = _placeholder_rows(version, language)
    if not texts:
        logger.info(
            "Translation backfill: version=%s language=%s nothing to do",
            version.id,
            language,
        )
        return stats

    started = time.perf_counter()
    translations = await translate_texts(
        texts,
        language,
        provider,
        fallback_provider,
        source_language=None,
        assumed_source_language=version.source_language,
        stats=stats,
    )

    updated = 0
    for row in rows:
        label = getattr(row, "label", None)
        if not isinstance(label, str):
            continue
        translated = translations.get(label)
        if translated and translated != label:
            row.label = translated  # type: ignore[attr-defined]
            updated += 1

    if updated:
        db.commit()

    logger.info(
        "Translation backfill: version=%s language=%s rows=%d updated=%d "
        "provider=%s provider_calls=%d characters=%d duration=%.2fs",
        version.id,
        language,
        len(rows),
        updated,
        stats.primary_provider or "-",
        stats.total_provider_calls,
        stats.translated_character_count,
        time.perf_counter() - started,
    )
    return stats
