"""AI provider Protocol and MockAIProvider.

The Protocol defines the contract that every provider must satisfy.
MockAIProvider provides fully deterministic responses without any external
calls — it is used in automated tests and as the default development provider.
"""

import json
import re
from typing import Protocol, runtime_checkable

from app.ai.schemas import (
    ClarificationRequest,
    ClarificationResult,
    ExplanationRequest,
    ExplanationResult,
    ExtractionRequest,
    ExtractionResult,
    QuestionGenerationRequest,
    QuestionGenerationResult,
    QuestionTranslationRequest,
    QuestionTranslationResult,
    TranslationRequest,
    TranslationResult,
)


def _parse_multiple_choice_answer(answer: str) -> list[str]:
    """Parses a multi-select answer submitted as a JSON array (the guided
    session's checkbox UI sends `JSON.stringify(selectedValues)`), falling
    back to a comma-separated string for any other caller.
    """
    try:
        parsed = json.loads(answer)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, list):
        return [str(v).strip() for v in parsed if str(v).strip()]
    return [v.strip() for v in answer.split(",") if v.strip()]


@runtime_checkable
class AIProvider(Protocol):
    """Provider-independent interface for all AI operations.

    Business services must import only this Protocol, never a concrete class.
    """

    async def extract_value(
        self,
        request: ExtractionRequest,
    ) -> ExtractionResult: ...

    async def explain_field(
        self,
        request: ExplanationRequest,
    ) -> ExplanationResult: ...

    async def clarify_answer(
        self,
        request: ClarificationRequest,
    ) -> ClarificationResult: ...

    async def translate_output(
        self,
        request: TranslationRequest,
    ) -> TranslationResult: ...

    async def translate_question(
        self,
        request: QuestionTranslationRequest,
    ) -> QuestionTranslationResult: ...

    async def generate_question(
        self,
        request: QuestionGenerationRequest,
    ) -> QuestionGenerationResult: ...

    async def health_check(self) -> bool: ...


# ---------------------------------------------------------------------------
# MockAIProvider
# ---------------------------------------------------------------------------


class MockAIProvider:
    """Deterministic AI provider for tests and local development.

    Rules:
    - Identical inputs always produce identical outputs.
    - No external HTTP calls, no network I/O.
    - Prompt contents and answer values are never logged.
    """

    async def extract_value(self, request: ExtractionRequest) -> ExtractionResult:
        field_type = request.field_type
        answer = request.answer.strip()

        if field_type == "person_name":
            return ExtractionResult(
                normalizedValue={"fullName": answer},
                outputValue=answer,
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type == "money":
            # Digits-only → missing currency and period
            if re.match(r"^\d+$", answer):
                return ExtractionResult(
                    normalizedValue={"amount": int(answer)},
                    outputValue=None,
                    requiresClarification=True,
                    uncertainties=["currency", "period"],
                )
            digits = "".join(c for c in answer if c.isdigit())
            amount = int(digits) if digits else 1800
            currency = "USD" if ("USD" in answer.upper() or "$" in answer) else "EUR"
            period = (
                "yearly"
                if ("YEAR" in answer.upper() or "ANNUAL" in answer.upper())
                else "monthly"
            )
            return ExtractionResult(
                normalizedValue={
                    "amount": amount,
                    "currency": currency,
                    "period": period,
                },
                outputValue=f"{amount} {currency} {period}",
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type == "date":
            return ExtractionResult(
                normalizedValue=answer,
                outputValue=answer,
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type == "boolean":
            val = answer.lower() in ("yes", "true", "1", "ja", "oui", "نعم")
            return ExtractionResult(
                normalizedValue=val,
                outputValue="true" if val else "false",
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type == "email":
            return ExtractionResult(
                normalizedValue=answer,
                outputValue=answer,
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type == "country":
            return ExtractionResult(
                normalizedValue=answer.upper()[:2],
                outputValue=answer.upper()[:2],
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type == "single_choice":
            return ExtractionResult(
                normalizedValue=answer,
                outputValue=answer,
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type == "multiple_choice":
            values = _parse_multiple_choice_answer(answer)
            return ExtractionResult(
                normalizedValue=values,
                outputValue=", ".join(values),
                requiresClarification=False,
                uncertainties=[],
            )

        if field_type in ("integer", "decimal"):
            digits = "".join(c for c in answer if c.isdigit() or c == ".")
            num: int | float
            try:
                num = int(digits) if field_type == "integer" else float(digits)
            except ValueError:
                num = 0
            return ExtractionResult(
                normalizedValue=num,
                outputValue=str(num),
                requiresClarification=False,
                uncertainties=[],
            )

        # Default: return raw answer as-is
        return ExtractionResult(
            normalizedValue=answer,
            outputValue=answer,
            requiresClarification=False,
            uncertainties=[],
        )

    async def explain_field(self, request: ExplanationRequest) -> ExplanationResult:
        return ExplanationResult(
            explanation=(
                f"[Mock] Please provide your '{request.field_label}' "
                f"({request.field_type}) in {request.user_language}."
            )
        )

    async def clarify_answer(
        self, request: ClarificationRequest
    ) -> ClarificationResult:
        missing = request.uncertainties or request.missing_fields  # type: ignore[attr-defined]
        question = (
            "[Mock] Please provide the following missing information: "
            + ", ".join(missing)
            if missing
            else "[Mock] Please elaborate on your answer."
        )
        return ClarificationResult(missingFields=missing, question=question)

    async def translate_output(self, request: TranslationRequest) -> TranslationResult:
        # In mock mode we return the original text unchanged
        return TranslationResult(translatedText=request.text)

    async def translate_question(
        self, request: QuestionTranslationRequest
    ) -> QuestionTranslationResult:
        lang = request.target_language
        return QuestionTranslationResult(
            text=f"[Mock Translation to {lang}] {request.text}",
            helpText=f"[Mock Translation to {lang}] {request.help_text}"
            if request.help_text
            else None,
            placeholder=f"[Mock Translation to {lang}] {request.placeholder}"
            if request.placeholder
            else None,
        )

    async def generate_question(
        self, request: QuestionGenerationRequest
    ) -> QuestionGenerationResult:
        key = request.question_key
        lang = request.target_language
        return QuestionGenerationResult(
            text=f"[Mock Question for {key} in {lang}]",
            helpText=f"[Mock Help Text for {key} in {lang}]",
            placeholder=f"[Mock Placeholder for {key} in {lang}]",
        )

    async def health_check(self) -> bool:
        return True
