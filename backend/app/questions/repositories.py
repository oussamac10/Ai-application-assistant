from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.questions.models import (
    QuestionDefinition,
    QuestionResolutionLog,
    QuestionTranslation,
)


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_definition(self, question_key: str) -> QuestionDefinition | None:
        """Retrieve a question definition by its unique semantic key."""
        stmt = (
            select(QuestionDefinition)
            .where(QuestionDefinition.question_key == question_key)
            .options(joinedload(QuestionDefinition.translations))
        )
        return self.db.scalars(stmt).first()

    def get_translation(
        self, definition_id: str, language: str
    ) -> QuestionTranslation | None:
        """Retrieve a specific translation for a definition."""
        stmt = select(QuestionTranslation).where(
            QuestionTranslation.question_definition_id == definition_id,
            QuestionTranslation.language == language,
        )
        return self.db.scalars(stmt).first()

    def get_approved_translation(
        self, question_key: str, language: str
    ) -> QuestionTranslation | None:
        """Retrieve the approved translation for a semantic key and language."""
        stmt = (
            select(QuestionTranslation)
            .join(QuestionDefinition)
            .where(
                QuestionDefinition.question_key == question_key,
                QuestionTranslation.language == language,
                QuestionTranslation.review_status == "approved",
                QuestionDefinition.is_active,
            )
        )
        return self.db.scalars(stmt).first()

    def get_pending_translation(
        self, question_key: str, language: str
    ) -> QuestionTranslation | None:
        """Retrieve the pending translation for a semantic key and language."""
        stmt = (
            select(QuestionTranslation)
            .join(QuestionDefinition)
            .where(
                QuestionDefinition.question_key == question_key,
                QuestionTranslation.language == language,
                QuestionTranslation.review_status == "pending_review",
                QuestionDefinition.is_active,
            )
        )
        return self.db.scalars(stmt).first()

    def get_translation_by_key_and_lang(
        self, question_key: str, language: str
    ) -> QuestionTranslation | None:
        """Retrieve any translation by semantic key and language."""
        stmt = (
            select(QuestionTranslation)
            .join(QuestionDefinition)
            .where(
                QuestionDefinition.question_key == question_key,
                QuestionTranslation.language == language,
                QuestionDefinition.is_active,
            )
        )
        return self.db.scalars(stmt).first()

    def get_translation_by_definition_and_lang(
        self, definition_id: str, language: str
    ) -> QuestionTranslation | None:
        """Retrieve a translation by definition ID and language."""
        stmt = select(QuestionTranslation).where(
            QuestionTranslation.question_definition_id == definition_id,
            QuestionTranslation.language == language,
        )
        return self.db.scalars(stmt).first()

    def create_definition(
        self,
        question_key: str,
        field_type: str,
        purpose: str = "collect_value",
        domain: str | None = None,
    ) -> QuestionDefinition:
        """Create a new question definition idempotently."""
        existing = self.get_definition(question_key)
        if existing:
            return existing
        definition = QuestionDefinition(
            question_key=question_key,
            field_type=field_type,
            purpose=purpose,
            domain=domain,
        )
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)
        return definition

    def create_translation(
        self,
        definition_id: str,
        language: str,
        text: str,
        help_text: str | None = None,
        placeholder: str | None = None,
        source: str = "manual",
        review_status: str = "approved",
        provider: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> QuestionTranslation:
        """Create or update a question translation idempotently."""
        existing = self.get_translation_by_definition_and_lang(definition_id, language)
        if existing:
            # If the translation is already approved, do not downgrade it to pending_review
            if existing.review_status != "approved" or review_status == "approved":
                existing.text = text
                existing.help_text = help_text
                existing.placeholder = placeholder
                existing.source = source
                existing.review_status = review_status
                existing.provider = provider
                existing.model = model
                existing.prompt_version = prompt_version
                if review_status == "approved":
                    existing.approved_at = datetime.now(UTC)
                self.db.commit()
                self.db.refresh(existing)
            return existing

        approved_at = datetime.now(UTC) if review_status == "approved" else None
        translation = QuestionTranslation(
            question_definition_id=definition_id,
            language=language,
            text=text,
            help_text=help_text,
            placeholder=placeholder,
            source=source,
            review_status=review_status,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            approved_at=approved_at,
        )
        self.db.add(translation)
        self.db.commit()
        self.db.refresh(translation)
        return translation

    def update_translation(
        self,
        translation_id: str,
        text: str,
        help_text: str | None = None,
        placeholder: str | None = None,
    ) -> QuestionTranslation:
        """Update an existing translation's text and metadata."""
        translation = self.db.get(QuestionTranslation, translation_id)
        if not translation:
            raise ValueError(f"Translation with ID '{translation_id}' not found.")
        translation.text = text
        translation.help_text = help_text
        translation.placeholder = placeholder
        self.db.commit()
        self.db.refresh(translation)
        return translation

    def approve_translation(self, translation_id: str) -> QuestionTranslation:
        """Mark a translation as approved."""
        translation = self.db.get(QuestionTranslation, translation_id)
        if not translation:
            raise ValueError(f"Translation with ID '{translation_id}' not found.")
        translation.review_status = "approved"
        translation.approved_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(translation)
        return translation

    def reject_translation(self, translation_id: str) -> QuestionTranslation:
        """Mark a translation as rejected."""
        translation = self.db.get(QuestionTranslation, translation_id)
        if not translation:
            raise ValueError(f"Translation with ID '{translation_id}' not found.")
        translation.review_status = "rejected"
        self.db.commit()
        self.db.refresh(translation)
        return translation

    def log_resolution(
        self,
        question_key: str,
        requested_language: str,
        resolved_language: str | None,
        source: str,
        used_ai: bool,
        provider: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
        result: str = "resolved",
    ) -> QuestionResolutionLog:
        """Log the result and provenance of a question resolution."""
        log_entry = QuestionResolutionLog(
            question_key=question_key,
            requested_language=requested_language,
            resolved_language=resolved_language,
            source=source,
            used_ai=used_ai,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            result=result,
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def list_questions(
        self,
        question_key: str | None = None,
        language: str | None = None,
        review_status: str | None = None,
        source: str | None = None,
    ) -> list[QuestionTranslation]:
        """List and filter catalog translations."""
        stmt = select(QuestionTranslation).join(QuestionDefinition)
        if question_key:
            stmt = stmt.where(QuestionDefinition.question_key == question_key)
        if language:
            stmt = stmt.where(QuestionTranslation.language == language)
        if review_status:
            stmt = stmt.where(QuestionTranslation.review_status == review_status)
        if source:
            stmt = stmt.where(QuestionTranslation.source == source)
        stmt = stmt.order_by(
            QuestionDefinition.question_key, QuestionTranslation.language
        )
        return list(self.db.scalars(stmt).all())
