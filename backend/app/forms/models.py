import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class FormTemplate(Base):
    __tablename__ = "form_templates"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    versions: Mapped[list["FormVersion"]] = relationship(
        "FormVersion",
        back_populates="template",
        passive_deletes="all",
        # Protect template deletion from silently cascading to versions
    )


class FormVersion(Base):
    __tablename__ = "form_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    form_template_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )  # draft, published, archived
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    # List of language strings
    supported_output_languages: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "form_template_id",
            "version_number",
            name="uq_form_template_version_number",
        ),
    )

    template: Mapped[FormTemplate] = relationship(
        "FormTemplate", back_populates="versions"
    )
    fields: Mapped[list["FormField"]] = relationship(
        "FormField",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="FormField.position",
    )


class FormField(Base):
    __tablename__ = "form_fields"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    form_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)
    required: Mapped[bool] = mapped_column(default=True, nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("form_version_id", "key", name="uq_form_version_field_key"),
    )

    version: Mapped[FormVersion] = relationship("FormVersion", back_populates="fields")
    translations: Mapped[list["FormFieldTranslation"]] = relationship(
        "FormFieldTranslation",
        back_populates="field",
        cascade="all, delete-orphan",
    )
    options: Mapped[list["FormFieldOption"]] = relationship(
        "FormFieldOption",
        back_populates="field",
        cascade="all, delete-orphan",
        order_by="FormFieldOption.position",
    )


class FormFieldTranslation(Base):
    __tablename__ = "form_field_translations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    form_field_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    help_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    placeholder: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "form_field_id", "language", name="uq_field_translation_language"
        ),
    )

    field: Mapped[FormField] = relationship("FormField", back_populates="translations")


class FormFieldOption(Base):
    __tablename__ = "form_field_options"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    form_field_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("form_field_id", "value", name="uq_field_option_value"),
    )

    field: Mapped[FormField] = relationship("FormField", back_populates="options")
    translations: Mapped[list["FormFieldOptionTranslation"]] = relationship(
        "FormFieldOptionTranslation",
        back_populates="option",
        cascade="all, delete-orphan",
    )


class FormFieldOptionTranslation(Base):
    __tablename__ = "form_field_option_translations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    form_field_option_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("form_field_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "form_field_option_id",
            "language",
            name="uq_field_option_translation_language",
        ),
    )

    option: Mapped[FormFieldOption] = relationship(
        "FormFieldOption", back_populates="translations"
    )
