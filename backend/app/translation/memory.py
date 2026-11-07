"""Translation Memory Service.

Provides instant 0ms caching and retrieval for administrative form field
and instruction translations across all forms and organizations.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.translation.models import TranslationMemory, hash_text

logger = logging.getLogger(__name__)


class TranslationMemoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_translations(
        self,
        text: str,
        source_language: str,
        target_languages: Sequence[str],
    ) -> dict[str, str]:
        """Looks up existing translations for the given text in translation memory."""
        clean_text = text.strip()
        if not clean_text or not target_languages:
            return {}

        text_hash = hash_text(clean_text)
        src_lang = source_language.strip().lower()
        target_set = {lang.strip().lower() for lang in target_languages}

        stmt = select(TranslationMemory).where(
            TranslationMemory.source_text_hash == text_hash,
            TranslationMemory.source_language == src_lang,
            TranslationMemory.target_language.in_(target_set),
        )
        records = self.db.scalars(stmt).all()
        return {r.target_language: r.translated_text for r in records}

    def save_translation(
        self,
        text: str,
        source_language: str,
        target_language: str,
        translated_text: str,
        provider: str = "gemini",
    ) -> TranslationMemory:
        """Stores or updates a translation in translation memory."""
        clean_text = text.strip()
        clean_trans = translated_text.strip()
        if not clean_text or not clean_trans:
            raise ValueError("Both text and translated_text must be non-empty.")

        text_hash = hash_text(clean_text)
        src_lang = source_language.strip().lower()
        tgt_lang = target_language.strip().lower()

        existing = self.db.scalar(
            select(TranslationMemory).where(
                TranslationMemory.source_text_hash == text_hash,
                TranslationMemory.source_language == src_lang,
                TranslationMemory.target_language == tgt_lang,
            )
        )
        if existing:
            existing.translated_text = clean_trans
            existing.provider = provider
            self.db.flush()
            return existing

        record = TranslationMemory(
            source_text_hash=text_hash,
            source_text=clean_text,
            source_language=src_lang,
            target_language=tgt_lang,
            translated_text=clean_trans,
            provider=provider,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def bulk_save_translations(
        self,
        text: str,
        source_language: str,
        translations: dict[str, str],
        provider: str = "gemini",
    ) -> None:
        """Saves multiple translations for a source text in a single transaction."""
        for target_lang, translated_val in translations.items():
            if translated_val and translated_val.strip():
                try:
                    self.save_translation(
                        text=text,
                        source_language=source_language,
                        target_language=target_lang,
                        translated_text=translated_val,
                        provider=provider,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to cache translation for %s -> %s: %s",
                        source_language,
                        target_lang,
                        e,
                    )
        self.db.commit()
