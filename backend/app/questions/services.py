from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.forms.services import (
    ResourceNotFoundError,
    StateConflictError,
)
from app.questions.models import QuestionDefinition, QuestionTranslation
from app.questions.repositories import QuestionRepository


class QuestionCatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QuestionRepository(db)

    def get_definition(self, question_key: str) -> QuestionDefinition:
        """Retrieve a definition or raise ResourceNotFoundError."""
        definition = self.repo.get_definition(question_key)
        if not definition:
            raise ResourceNotFoundError(
                f"Question definition with key '{question_key}' not found."
            )
        return definition

    def create_definition(
        self,
        question_key: str,
        field_type: str,
        purpose: str = "collect_value",
        domain: str | None = None,
    ) -> QuestionDefinition:
        """Create a definition, enforcing unique semantic keys."""
        existing = self.repo.get_definition(question_key)
        if existing:
            raise StateConflictError(
                f"Question definition with key '{question_key}' already exists."
            )
        return self.repo.create_definition(
            question_key=question_key,
            field_type=field_type,
            purpose=purpose,
            domain=domain,
        )

    def create_manual_translation(
        self,
        question_key: str,
        language: str,
        text: str,
        help_text: str | None = None,
        placeholder: str | None = None,
    ) -> QuestionTranslation:
        """Create or update a manual translation, ensuring approved is not overwritten."""
        definition = self.get_definition(question_key)
        existing = self.repo.get_translation(definition.id, language)

        if existing:
            # Enforce that approved manual/fixture content cannot be overwritten
            # automatically/without explicit action.
            if existing.review_status == "approved" and existing.source in (
                "manual",
                "fixture",
            ):
                raise StateConflictError(
                    f"Approved manual/fixture translation for '{question_key}' "
                    f"in language '{language}' already exists."
                )

            # Otherwise, update the existing pending/rejected translation
            existing.text = text
            existing.help_text = help_text
            existing.placeholder = placeholder
            existing.source = "manual"
            existing.review_status = "approved"
            existing.approved_at = datetime.now(UTC)
            self.db.commit()
            return existing

        translation = self.repo.create_translation(
            definition_id=definition.id,
            language=language,
            text=text,
            help_text=help_text,
            placeholder=placeholder,
            source="manual",
            review_status="approved",
        )
        return translation


class QuestionReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QuestionRepository(db)

    def approve_translation(
        self, question_key: str, language: str
    ) -> QuestionTranslation:
        """Transition a pending translation to approved status."""
        definition = self.repo.get_definition(question_key)
        if not definition:
            raise ResourceNotFoundError(
                f"Question definition with key '{question_key}' not found."
            )

        translation = self.repo.get_translation(definition.id, language)
        if not translation:
            raise ResourceNotFoundError(
                f"Translation for '{question_key}' in language '{language}' not found."
            )

        if translation.review_status != "pending_review":
            status_val = translation.review_status
            raise StateConflictError(
                f"Cannot approve translation. Current status is '{status_val}' "
                f"(expected 'pending_review')."
            )

        return self.repo.approve_translation(translation.id)

    def reject_translation(
        self, question_key: str, language: str
    ) -> QuestionTranslation:
        """Transition a pending translation to rejected status."""
        definition = self.repo.get_definition(question_key)
        if not definition:
            raise ResourceNotFoundError(
                f"Question definition with key '{question_key}' not found."
            )

        translation = self.repo.get_translation(definition.id, language)
        if not translation:
            raise ResourceNotFoundError(
                f"Translation for '{question_key}' in language '{language}' not found."
            )

        if translation.review_status != "pending_review":
            status_val = translation.review_status
            raise StateConflictError(
                f"Cannot reject translation. Current status is '{status_val}' "
                f"(expected 'pending_review')."
            )

        return self.repo.reject_translation(translation.id)
