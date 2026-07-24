from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.forms.models import (
    FormField,
    FormFieldOption,
    FormFieldOptionTranslation,
    FormFieldTranslation,
    FormTemplate,
    FormVersion,
)
from app.forms.repositories import FormRepository
from app.forms.schemas import FieldCreate, FieldUpdate
from app.forms.validation.config_validation import (
    ConfigurationValidationError,
    validate_field_configuration,
)


class ResourceNotFoundError(Exception):
    """Raised when a requested resource is not found."""

    pass


class StateConflictError(Exception):
    """Raised when a state transition or mutation conflicts with current status."""

    pass


class ValidationError(Exception):
    """Raised when business logic validation fails."""

    pass


class FormService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FormRepository(db)

    # Template
    def create_template(
        self, key: str, name: str, description: str | None = None
    ) -> FormTemplate:
        existing = self.repo.get_template_by_key(key)
        if existing:
            raise StateConflictError(f"Form template with key '{key}' already exists.")
        return self.repo.create_template(key, name, description)

    def list_templates(self) -> list[FormTemplate]:
        return self.repo.list_templates()

    def get_template(self, template_id: str) -> FormTemplate:
        template = self.repo.get_template(template_id)
        if not template:
            raise ResourceNotFoundError(
                f"Form template with ID '{template_id}' not found."
            )
        return template

    # Version
    def create_draft_version(
        self,
        form_template_id: str,
        source_language: str,
        supported_output_languages: list[str],
    ) -> FormVersion:
        # Verify template exists
        self.get_template(form_template_id)

        # Get next version number
        latest_num = self.repo.get_latest_version_number(form_template_id)
        next_num = latest_num + 1

        return self.repo.create_version(
            form_template_id=form_template_id,
            source_language=source_language,
            supported_output_languages=supported_output_languages,
            version_number=next_num,
            status="draft",
        )

    def get_version(self, version_id: str) -> FormVersion:
        version = self.repo.get_version(version_id)
        if not version:
            raise ResourceNotFoundError(
                f"Form version with ID '{version_id}' not found."
            )
        return version

    # Field
    def add_field_to_draft(self, version_id: str, field_data: FieldCreate) -> FormField:
        version = self.get_version(version_id)
        if version.status != "draft":
            raise StateConflictError("Cannot add fields to a non-draft version.")

        # Check key uniqueness
        existing_field = self.repo.get_field_by_key(version_id, field_data.key)
        if existing_field:
            raise StateConflictError(
                f"Field with key '{field_data.key}' already exists in this version."
            )

        # Validate configuration
        try:
            validate_field_configuration(
                field_data.field_type, field_data.configuration
            )
        except ConfigurationValidationError as e:
            raise ValidationError(str(e)) from e

        # Check options constraints
        is_choice = field_data.field_type in ("single_choice", "multiple_choice")
        if is_choice:
            if not field_data.options:
                raise ValidationError(
                    f"Choice field '{field_data.key}' must have options."
                )
            # Check option values are unique
            seen_options = set()
            for opt in field_data.options:
                if opt.value in seen_options:
                    raise ValidationError(
                        f"Duplicate option value '{opt.value}' "
                        f"in field '{field_data.key}'."
                    )
                seen_options.add(opt.value)
        else:
            if field_data.options:
                raise ValidationError(
                    f"Non-choice field '{field_data.key}' cannot have options."
                )

        # Insert field
        field = self.repo.add_field(
            form_version_id=version_id,
            key=field_data.key,
            field_type=field_data.field_type,
            required=field_data.required,
            position=field_data.position,
            configuration=field_data.configuration,
            question_key=field_data.question_key,
        )

        # Insert translations
        for t in field_data.translations:
            self.repo.add_field_translation(
                form_field_id=field.id,
                language=t.language,
                label=t.label,
                help_text=t.help_text,
                placeholder=t.placeholder,
            )

        # Insert options
        if is_choice:
            for opt in field_data.options:
                db_opt = self.repo.add_field_option(
                    form_field_id=field.id, value=opt.value, position=opt.position
                )
                self.db.flush()  # get db_opt.id
                for ot in opt.translations:
                    self.repo.add_option_translation(
                        form_field_option_id=db_opt.id,
                        language=ot.language,
                        label=ot.label,
                    )

        self.db.commit()
        # Refresh to load relationships
        return self.repo.get_field(field.id)  # type: ignore

    def update_draft_field(self, field_id: str, field_data: FieldUpdate) -> FormField:
        field = self.repo.get_field(field_id)
        if not field:
            raise ResourceNotFoundError(f"Field with ID '{field_id}' not found.")

        version = self.repo.get_version(field.form_version_id)
        if not version or version.status != "draft":
            raise StateConflictError("Cannot update fields in a non-draft version.")

        # Update basic fields if provided
        if field_data.key is not None and field_data.key != field.key:
            # Check key uniqueness
            existing = self.repo.get_field_by_key(field.form_version_id, field_data.key)
            if existing:
                raise StateConflictError(
                    f"Field with key '{field_data.key}' already exists in this version."
                )
            field.key = field_data.key

        if field_data.field_type is not None:
            field.field_type = field_data.field_type

        if field_data.required is not None:
            field.required = field_data.required

        if field_data.position is not None:
            field.position = field_data.position

        if field_data.question_key is not None:
            # Allow setting it to empty string or None to clear it/change it
            field.question_key = (
                field_data.question_key if field_data.question_key != "" else None
            )

        # Update configuration
        new_config = field.configuration
        if field_data.configuration is not None:
            new_config = field_data.configuration
            field.configuration = new_config

        # Validate final configuration
        try:
            validate_field_configuration(field.field_type, new_config)
        except ConfigurationValidationError as e:
            raise ValidationError(str(e)) from e

        # Update translations if provided
        if field_data.translations is not None:
            # Clear existing translations
            for trans in list(field.translations):
                self.db.delete(trans)
            # Add new translations
            for t in field_data.translations:
                self.repo.add_field_translation(
                    form_field_id=field.id,
                    language=t.language,
                    label=t.label,
                    help_text=t.help_text,
                    placeholder=t.placeholder,
                )

        # Update options if provided
        is_choice = field.field_type in ("single_choice", "multiple_choice")
        if field_data.options is not None:
            if not is_choice and field_data.options:
                raise ValidationError(
                    f"Non-choice field '{field.key}' cannot have options."
                )
            if is_choice and not field_data.options:
                raise ValidationError(f"Choice field '{field.key}' must have options.")

            # Clear options
            for opt in list(field.options):
                self.db.delete(opt)

            # Add new options
            if is_choice:
                seen_options = set()
                options_to_add = field_data.options or []
                for opt_data in options_to_add:
                    if opt_data.value in seen_options:
                        raise ValidationError(
                            f"Duplicate option value '{opt_data.value}'."
                        )
                    seen_options.add(opt_data.value)

                    db_opt = self.repo.add_field_option(
                        form_field_id=field.id,
                        value=opt_data.value,
                        position=opt_data.position,
                    )
                    self.db.flush()
                    for ot in opt_data.translations:
                        self.repo.add_option_translation(
                            form_field_option_id=db_opt.id,
                            language=ot.language,
                            label=ot.label,
                        )

        self.db.commit()
        return self.repo.get_field(field.id)  # type: ignore

    # Publish
    def publish_version(self, version_id: str) -> FormVersion:
        version = self.get_version(version_id)
        if version.status != "draft":
            raise StateConflictError("Only draft versions can be published.")

        if not version.fields:
            raise ValidationError("Cannot publish a form version with no fields.")

        # Check unique keys and deterministic validation
        seen_keys = set()
        for field in version.fields:
            if field.key in seen_keys:
                raise ValidationError(f"Duplicate field key '{field.key}' in version.")
            seen_keys.add(field.key)

            # Check configuration is valid
            try:
                validate_field_configuration(field.field_type, field.configuration)
            except ConfigurationValidationError as e:
                raise ValidationError(f"Field '{field.key}': {e}") from e

            # Check translation for source language exists and has label
            source_trans = next(
                (
                    t
                    for t in field.translations
                    if t.language == version.source_language
                ),
                None,
            )
            if not source_trans or not source_trans.label.strip():
                raise ValidationError(
                    f"Source language ({version.source_language}) label "
                    f"is missing for field '{field.key}'."
                )

            # Choices constraints
            is_choice = field.field_type in ("single_choice", "multiple_choice")
            if is_choice:
                if not field.options:
                    raise ValidationError(
                        f"Choice field '{field.key}' must have options."
                    )
                # Option translations for all supported languages
                req_languages = set(version.supported_output_languages) | {
                    version.source_language
                }
                for opt in field.options:
                    opt_langs = {t.language for t in opt.translations}
                    for lang in req_languages:
                        if lang not in opt_langs:
                            raise ValidationError(
                                f"Option '{opt.value}' of field '{field.key}' "
                                f"is missing translation for language '{lang}'."
                            )
            else:
                if field.options:
                    raise ValidationError(
                        f"Non-choice field '{field.key}' has options."
                    )

        # Mark as published
        version.status = "published"
        version.published_at = datetime.now(UTC)
        self.db.commit()
        return version

    # Clone
    def clone_version(self, version_id: str) -> FormVersion:
        version = self.get_version(version_id)

        # Get next version number
        latest_num = self.repo.get_latest_version_number(version.form_template_id)
        next_num = latest_num + 1

        # Create new version record
        new_version = self.repo.create_version(
            form_template_id=version.form_template_id,
            source_language=version.source_language,
            supported_output_languages=version.supported_output_languages,
            version_number=next_num,
            status="draft",
        )

        # Copy fields and child entities
        for field in version.fields:
            # Copy field
            new_field = FormField(
                form_version_id=new_version.id,
                key=field.key,
                field_type=field.field_type,
                required=field.required,
                position=field.position,
                configuration=field.configuration,
                question_key=field.question_key,
            )
            self.db.add(new_field)
            self.db.flush()

            # Copy translations
            for trans in field.translations:
                new_trans = FormFieldTranslation(
                    form_field_id=new_field.id,
                    language=trans.language,
                    label=trans.label,
                    help_text=trans.help_text,
                    placeholder=trans.placeholder,
                )
                self.db.add(new_trans)

            # Copy options
            for opt in field.options:
                new_opt = FormFieldOption(
                    form_field_id=new_field.id,
                    value=opt.value,
                    position=opt.position,
                )
                self.db.add(new_opt)
                self.db.flush()

                # Copy option translations
                for ot in opt.translations:
                    new_ot = FormFieldOptionTranslation(
                        form_field_option_id=new_opt.id,
                        language=ot.language,
                        label=ot.label,
                    )
                    self.db.add(new_ot)

        self.db.commit()
        return self.repo.get_version(new_version.id)  # type: ignore
