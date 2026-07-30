"""Pydantic schemas for the AI provider interface.

These schemas define the contract between the business service layer and any
AI provider (Mock, Ollama, future cloud providers).  The service layer imports
only these schemas; provider implementations are never imported directly.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# ExtractionRequest / ExtractionResult
# ---------------------------------------------------------------------------


class ExtractionRequest(BaseModel):
    """Ask the provider to extract a canonical value from free-text input."""

    model_config = ConfigDict(populate_by_name=True)

    field_type: str = Field(alias="fieldType")
    field_config: dict[str, Any] = Field(default_factory=dict, alias="fieldConfig")
    answer: str
    user_language: str = Field(alias="userLanguage")
    source_language: str = Field(alias="sourceLanguage")
    output_language: str = Field(alias="outputLanguage")


class ExtractionResult(BaseModel):
    """Structured extraction result returned by any AI provider."""

    model_config = ConfigDict(populate_by_name=True)

    normalized_value: Any = Field(alias="normalizedValue")
    output_value: str | None = Field(default=None, alias="outputValue")
    requires_clarification: bool = Field(alias="requiresClarification")
    uncertainties: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ExplanationRequest / ExplanationResult
# ---------------------------------------------------------------------------


class ExplanationRequest(BaseModel):
    """Ask the provider to explain a form field in the user's language."""

    model_config = ConfigDict(populate_by_name=True)

    field_type: str = Field(alias="fieldType")
    field_label: str = Field(alias="fieldLabel")
    field_config: dict[str, Any] = Field(default_factory=dict, alias="fieldConfig")
    user_language: str = Field(alias="userLanguage")
    source_language: str = Field(alias="sourceLanguage")


class ExplanationResult(BaseModel):
    """Plain-text field explanation returned by any AI provider."""

    model_config = ConfigDict(populate_by_name=True)

    explanation: str


# ---------------------------------------------------------------------------
# ClarificationRequest / ClarificationResult
# ---------------------------------------------------------------------------


class ClarificationRequest(BaseModel):
    """Ask the provider which pieces of information are still missing."""

    model_config = ConfigDict(populate_by_name=True)

    field_type: str = Field(alias="fieldType")
    field_config: dict[str, Any] = Field(default_factory=dict, alias="fieldConfig")
    partial_normalized_value: dict[str, Any] = Field(
        alias="partialNormalizedValue", default_factory=dict
    )
    uncertainties: list[str] = Field(default_factory=list)
    user_language: str = Field(alias="userLanguage")
    source_language: str = Field(alias="sourceLanguage")
    output_language: str = Field(alias="outputLanguage")


class ClarificationResult(BaseModel):
    """Structured clarification proposal returned by any AI provider."""

    model_config = ConfigDict(populate_by_name=True)

    missing_fields: list[str] = Field(alias="missingFields", default_factory=list)
    question: str


# ---------------------------------------------------------------------------
# TranslationRequest / TranslationResult
# ---------------------------------------------------------------------------


class TranslationRequest(BaseModel):
    """Ask the provider to translate a dynamic user-supplied text fragment."""

    model_config = ConfigDict(populate_by_name=True)

    text: str
    source_language: str = Field(alias="sourceLanguage")
    target_language: str = Field(alias="targetLanguage")


class TranslationResult(BaseModel):
    """Translation returned by any AI provider."""

    model_config = ConfigDict(populate_by_name=True)

    translated_text: str = Field(alias="translatedText")


class BatchTranslationItem(BaseModel):
    """One text to translate, carried with the stable id the caller uses to
    map the result back. The id is the caller's own index — never the field
    key or any other application identifier, so nothing about the document
    leaves via the id."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    text: str


class BatchTranslationRequest(BaseModel):
    """Translate several texts into ONE target language in a single provider
    call. One language per request keeps the instruction unambiguous for
    small local models, which measurably degrade when asked to produce two
    target languages at once."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[BatchTranslationItem]
    source_language: str = Field(alias="sourceLanguage")
    target_language: str = Field(alias="targetLanguage")


class BatchTranslationResult(BaseModel):
    """Translations keyed by the request's item ids.

    Deliberately a mapping rather than a list: a provider that returns items
    out of order, drops one, or repeats one cannot silently shift every
    later translation onto the wrong field. Missing ids are the caller's
    signal to fall back for exactly those items (see
    `app/ai/batch_translation.py`).
    """

    model_config = ConfigDict(populate_by_name=True)

    translations_by_id: dict[int, str] = Field(alias="translationsById")


class QuestionTranslationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_key: str = Field(alias="questionKey")
    field_type: str = Field(alias="fieldType")
    text: str
    help_text: str | None = Field(default=None, alias="helpText")
    placeholder: str | None = Field(default=None, alias="placeholder")
    source_language: str = Field(alias="sourceLanguage")
    target_language: str = Field(alias="targetLanguage")


class QuestionTranslationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    help_text: str | None = Field(default=None, alias="helpText")
    placeholder: str | None = Field(default=None, alias="placeholder")


class QuestionGenerationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_key: str = Field(alias="questionKey")
    field_type: str = Field(alias="fieldType")
    purpose: str = "collect_value"
    required: bool = True
    target_language: str = Field(alias="targetLanguage")
    field_config: dict[str, Any] = Field(default_factory=dict, alias="fieldConfig")


class QuestionGenerationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    help_text: str | None = Field(default=None, alias="helpText")
    placeholder: str | None = Field(default=None, alias="placeholder")
