from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.forms.models import (
    FormField,
    FormFieldOption,
    FormFieldOptionTranslation,
    FormFieldTranslation,
    FormTemplate,
    FormVersion,
)


class FormRepository:
    def __init__(self, db: Session):
        self.db = db

    # Template operations
    def create_template(
        self, key: str, name: str, description: str | None = None
    ) -> FormTemplate:
        template = FormTemplate(key=key, name=name, description=description)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_template(self, template_id: str) -> FormTemplate | None:
        return self.db.get(FormTemplate, template_id)

    def get_template_by_key(self, key: str) -> FormTemplate | None:
        stmt = select(FormTemplate).where(FormTemplate.key == key)
        return self.db.scalars(stmt).first()

    def list_templates(self) -> list[FormTemplate]:
        stmt = select(FormTemplate).order_by(FormTemplate.created_at.desc())
        return list(self.db.scalars(stmt).all())

    # Version operations
    def create_version(
        self,
        form_template_id: str,
        source_language: str,
        supported_output_languages: list[str],
        version_number: int,
        status: str = "draft",
        origin: str = "predefined_template",
        pdf_template_key: str | None = None,
    ) -> FormVersion:
        version = FormVersion(
            form_template_id=form_template_id,
            source_language=source_language,
            supported_output_languages=supported_output_languages,
            version_number=version_number,
            status=status,
            origin=origin,
            pdf_template_key=pdf_template_key,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_version(self, version_id: str) -> FormVersion | None:
        # Load version with fields, options, translations, option translations
        stmt = (
            select(FormVersion)
            .where(FormVersion.id == version_id)
            .options(
                joinedload(FormVersion.fields).joinedload(FormField.translations),
                joinedload(FormVersion.fields)
                .joinedload(FormField.options)
                .joinedload(FormFieldOption.translations),
            )
        )
        return self.db.scalars(stmt).first()

    def get_latest_version_number(self, template_id: str) -> int:
        stmt = (
            select(FormVersion.version_number)
            .where(FormVersion.form_template_id == template_id)
            .order_by(FormVersion.version_number.desc())
            .limit(1)
        )
        val = self.db.scalars(stmt).first()
        return val if val is not None else 0

    # Field operations
    def get_field(self, field_id: str) -> FormField | None:
        stmt = (
            select(FormField)
            .where(FormField.id == field_id)
            .options(
                joinedload(FormField.translations),
                joinedload(FormField.options).joinedload(FormFieldOption.translations),
            )
        )
        return self.db.scalars(stmt).first()

    def get_field_by_key(self, version_id: str, key: str) -> FormField | None:
        stmt = select(FormField).where(
            FormField.form_version_id == version_id, FormField.key == key
        )
        return self.db.scalars(stmt).first()

    def add_field(
        self,
        form_version_id: str,
        key: str,
        field_type: str,
        required: bool,
        position: int,
        configuration: dict[str, Any],
        question_key: str | None = None,
        requiredness: str = "unknown",
    ) -> FormField:
        field = FormField(
            form_version_id=form_version_id,
            key=key,
            field_type=field_type,
            required=required,
            requiredness=requiredness,
            position=position,
            configuration=configuration,
            question_key=question_key,
        )
        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)
        return field

    def add_field_translation(
        self,
        form_field_id: str,
        language: str,
        label: str,
        help_text: str | None = None,
        placeholder: str | None = None,
    ) -> FormFieldTranslation:
        translation = FormFieldTranslation(
            form_field_id=form_field_id,
            language=language,
            label=label,
            help_text=help_text,
            placeholder=placeholder,
        )
        self.db.add(translation)
        return translation

    def add_field_option(
        self, form_field_id: str, value: str, position: int
    ) -> FormFieldOption:
        option = FormFieldOption(
            form_field_id=form_field_id, value=value, position=position
        )
        self.db.add(option)
        return option

    def add_option_translation(
        self, form_field_option_id: str, language: str, label: str
    ) -> FormFieldOptionTranslation:
        translation = FormFieldOptionTranslation(
            form_field_option_id=form_field_option_id,
            language=language,
            label=label,
        )
        self.db.add(translation)
        return translation
