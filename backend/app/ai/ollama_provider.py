"""OllamaAIProvider — calls a local Ollama instance for AI operations.

Design rules (see docs/ai-provider.md):
- All requests use stream=false, format="json", and think=false.
- Responses are validated with Pydantic before use.
- Timeouts and retries are bounded.
- No sensitive content (answers, tokens, secrets) is ever logged.
- Prompt templates are loaded from the prompts/ directory at import time.
- The backend must reach Ollama via OLLAMA_BASE_URL (host.docker.internal in Docker).
- Prompt injection: user-supplied text is embedded only as a value in a
  structured JSON payload and is marked as untrusted in the prompt template.

Why think=false: qwen3 (and other reasoning-capable models) default to
splitting output into a "thinking" field (chain-of-thought) and a
"response" field (the final answer). When the model never emits an
explicit end-of-thinking marker — which reliably happens for a prompt that
demands raw JSON with "no commentary" — Ollama attributes the *entire*
output to "thinking" and leaves "response" empty, even though `done_reason`
is "stop" (not an error). Disabling thinking mode makes the model return
its full answer in "response" every time, and doubles as the enforcement
mechanism for "never expose chain-of-thought": there is no thinking content
to accidentally log or leak. `thinking` is therefore never read.
"""

from __future__ import annotations

import json
import logging
import pathlib
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.ai.errors import (
    AIProviderMalformedResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIProviderValidationError,
)
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

logger = logging.getLogger(__name__)

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


# Load prompt templates once at module import time
_EXTRACT_PROMPT = _load_prompt("extract_value_v1.txt")
_EXPLAIN_PROMPT = _load_prompt("explain_field_v1.txt")
_CLARIFY_PROMPT = _load_prompt("clarify_answer_v1.txt")
_TRANSLATE_PROMPT = _load_prompt("translate_output_v1.txt")
_TRANSLATE_QUESTION_PROMPT = _load_prompt("translate_question_v1.txt")
_GENERATE_QUESTION_PROMPT = _load_prompt("generate_question_v1.txt")


def _fill_template(template: str, variables: dict[str, str]) -> str:
    """Replace {{key}} placeholders in a template string."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


_JSON_REPAIR_SUFFIX = (
    "\n\nYour previous response was empty or was not valid JSON. "
    "Respond again with ONLY valid JSON matching the schema above — "
    "no markdown, no commentary, no additional text."
)


class _ExtractValueSchema(BaseModel):
    """The exact wire shape required of Ollama's raw JSON for value
    extraction. `extra="forbid"` rejects any response whose top-level keys
    don't match this schema exactly — in particular a model that embeds its
    reasoning as an object key instead of following the schema (observed:
    `{"The user's answer '...' translates to '...' ...": "marié"}`) is
    rejected outright rather than silently accepted via a lenient `.get()`.
    Only `requiresClarification` is required; the others default so a model
    that omits an empty/null field isn't punished for that alone.
    """

    model_config = ConfigDict(extra="forbid")

    normalizedValue: Any = None
    outputValue: str | None = None
    requiresClarification: bool
    uncertainties: list[str] = Field(default_factory=list)


# Field types whose documented (extract_value_v1.txt) normalizedValue shape
# is itself a structured object/array — every other field type must receive
# a plain scalar or null. This is what actually catches the reported bug:
# the malformed response above has the *correct* top-level keys (the
# reasoning object was nested inside "normalizedValue", not used as a
# top-level key) but is a dict for a "multiline_text" field, which is not
# a documented shape for that field type.
_STRUCTURED_VALUE_FIELD_TYPES = frozenset({"money", "person_name"})
_ARRAY_VALUE_FIELD_TYPES = frozenset({"multiple_choice"})


def _normalized_value_shape_is_valid(field_type: str, value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, dict):
        return field_type in _STRUCTURED_VALUE_FIELD_TYPES
    if isinstance(value, list):
        return field_type in _ARRAY_VALUE_FIELD_TYPES
    return True


class OllamaAIProvider:
    """AI provider that calls a local Ollama instance.

    Parameters
    ----------
    base_url:
        HTTP base URL of the Ollama server (e.g. http://host.docker.internal:11434).
    model:
        Name of the Ollama model to use (e.g. qwen3:4b).
    timeout_seconds:
        Maximum seconds to wait for a single Ollama response.
    max_retries:
        How many times to retry a failed request before raising.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 1,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = httpx.Timeout(timeout=float(timeout_seconds))
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
        }

    async def _post(self, payload: dict[str, Any]) -> str:
        """POST to Ollama /api/generate with bounded retries for transient
        transport failures (timeouts only — connection/HTTP errors are not
        retried since they will not resolve on their own within one
        request). Returns the raw `response` text; `thinking` is
        intentionally never read.

        The prompt/answer text is never logged — only exception types and
        HTTP status codes, so the true cause (connection failure, timeout,
        model not found, ...) is diagnosable from logs without exposing
        user data.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/api/generate",
                        json=payload,
                    )
                    response.raise_for_status()

                raw = response.json()
                return str(raw.get("response") or "")

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Ollama request timed out (attempt %d/%d, timeout=%ss)",
                    attempt + 1,
                    self._max_retries + 1,
                    self._timeout.read,
                )
            except httpx.ConnectError as exc:
                logger.error("Cannot connect to Ollama at %s", self._base_url)
                raise AIProviderUnavailableError(
                    "Cannot connect to Ollama service"
                ) from exc
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    logger.error(
                        "Ollama model '%s' not found (HTTP 404) — is it pulled?",
                        self._model,
                    )
                else:
                    logger.error("Ollama returned HTTP %d", status)
                raise AIProviderUnavailableError(
                    f"Ollama returned HTTP {status}"
                ) from exc
            except Exception as exc:
                logger.error(
                    "Unexpected error communicating with Ollama: %s",
                    type(exc).__name__,
                )
                raise AIProviderUnavailableError(
                    "Unexpected error communicating with Ollama"
                ) from exc

        logger.error(
            "Ollama did not respond after %d attempt(s)", self._max_retries + 1
        )
        raise AIProviderTimeoutError(
            f"Ollama did not respond after {self._max_retries + 1} attempt(s)"
        ) from last_error

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        if not text.strip():
            return None
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    async def _call_ollama(self, prompt: str) -> dict[str, Any]:
        """Requests a JSON object from Ollama for the given prompt.

        If the first response is empty or not valid JSON, makes exactly one
        repair attempt with an added instruction before giving up — this
        does not re-submit or duplicate anything on the application side
        (no answer is persisted until a valid result is returned to the
        caller), it only asks the model again for a well-formed reply.
        """
        payload = self._build_payload(prompt)
        text = await self._post(payload)
        parsed = self._try_parse_json(text)
        if parsed is not None:
            return parsed

        if not text.strip():
            logger.warning("Ollama returned an empty response; retrying once")
        else:
            logger.warning("Ollama returned non-JSON content; retrying once")

        repair_payload = self._build_payload(prompt + _JSON_REPAIR_SUFFIX)
        repair_text = await self._post(repair_payload)
        repaired = self._try_parse_json(repair_text)
        if repaired is not None:
            return repaired

        if not repair_text.strip():
            logger.error("Ollama returned an empty response after repair retry")
            raise AIProviderMalformedResponseError("Ollama returned an empty response")

        logger.error("Ollama returned non-JSON content after repair retry")
        raise AIProviderMalformedResponseError("Ollama returned non-JSON content")

    @staticmethod
    def _safe_validate(
        parsed: dict[str, Any] | None,
        validate: Callable[[dict[str, Any]], Any],
    ) -> Any | None:
        if parsed is None:
            return None
        try:
            return validate(parsed)
        except Exception:
            return None

    async def _call_ollama_structured(
        self,
        prompt: str,
        validate: Callable[[dict[str, Any]], Any],
    ) -> Any:
        """Like `_call_ollama`, but additionally enforces a strict response
        schema — not just JSON syntax — within the same bounded repair
        budget: a response that is syntactically valid JSON but has the
        wrong shape (including, but not limited to, the model embedding its
        reasoning in place of a real value) is treated exactly like
        malformed JSON and triggers the same single repair retry, never a
        second retry stacked on top of it. Never exposes the raw model text
        in a raised exception — only a generic, safe message.
        """
        payload = self._build_payload(prompt)
        text = await self._post(payload)
        parsed = self._try_parse_json(text)
        validated = self._safe_validate(parsed, validate)
        if validated is not None:
            return validated

        if not text.strip():
            logger.warning("Ollama returned an empty response; retrying once")
        elif parsed is None:
            logger.warning("Ollama returned non-JSON content; retrying once")
        else:
            logger.warning(
                "Ollama returned JSON that did not match the required schema; "
                "retrying once"
            )

        repair_payload = self._build_payload(prompt + _JSON_REPAIR_SUFFIX)
        repair_text = await self._post(repair_payload)
        repair_parsed = self._try_parse_json(repair_text)
        repair_validated = self._safe_validate(repair_parsed, validate)
        if repair_validated is not None:
            return repair_validated

        if not repair_text.strip() or repair_parsed is None:
            logger.error("Ollama returned malformed content after repair retry")
            raise AIProviderMalformedResponseError("Ollama returned malformed content")

        logger.error(
            "Ollama response did not match the required schema after repair retry"
        )
        raise AIProviderValidationError(
            "Ollama response does not match the required extraction schema"
        )

    def _validate(
        self,
        data: dict[str, Any],
        schema: type,
        *,
        by_alias: bool = False,
    ) -> Any:
        """Validate raw dict with a Pydantic model; raise on mismatch."""
        try:
            return schema(**data)
        except Exception as exc:
            raise AIProviderValidationError(
                f"Ollama response does not match {schema.__name__}"
            ) from exc

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    async def extract_value(self, request: ExtractionRequest) -> ExtractionResult:
        prompt = _fill_template(
            _EXTRACT_PROMPT,
            {
                "field_type": request.field_type,
                "field_config": json.dumps(request.field_config),
                "answer": request.answer,
                "user_language": request.user_language,
                "source_language": request.source_language,
                "output_language": request.output_language,
            },
        )

        field_type = request.field_type

        def validate(data: dict[str, Any]) -> _ExtractValueSchema:
            parsed = _ExtractValueSchema.model_validate(data)
            if not _normalized_value_shape_is_valid(field_type, parsed.normalizedValue):
                raise ValueError(
                    "normalizedValue has an unexpected shape for this field type"
                )
            return parsed

        validated: _ExtractValueSchema = await self._call_ollama_structured(
            prompt, validate
        )
        return ExtractionResult(
            normalizedValue=validated.normalizedValue,
            outputValue=validated.outputValue,
            requiresClarification=validated.requiresClarification,
            uncertainties=validated.uncertainties,
        )

    async def explain_field(self, request: ExplanationRequest) -> ExplanationResult:
        prompt = _fill_template(
            _EXPLAIN_PROMPT,
            {
                "field_type": request.field_type,
                "field_label": request.field_label,
                "field_config": json.dumps(request.field_config),
                "user_language": request.user_language,
                "source_language": request.source_language,
            },
        )
        raw = await self._call_ollama(prompt)
        if "explanation" not in raw:
            raise AIProviderValidationError("Ollama response missing 'explanation' key")
        return ExplanationResult(explanation=str(raw["explanation"]))

    async def clarify_answer(
        self, request: ClarificationRequest
    ) -> ClarificationResult:
        prompt = _fill_template(
            _CLARIFY_PROMPT,
            {
                "field_type": request.field_type,
                "field_config": json.dumps(request.field_config),
                "partial_normalized_value": json.dumps(
                    request.partial_normalized_value
                ),
                "uncertainties": json.dumps(request.uncertainties),
                "user_language": request.user_language,
                "source_language": request.source_language,
                "output_language": request.output_language,
            },
        )
        raw = await self._call_ollama(prompt)
        return ClarificationResult(
            missingFields=list(raw.get("missingFields", [])),
            question=str(raw.get("question", "")),
        )

    async def translate_output(self, request: TranslationRequest) -> TranslationResult:
        prompt = _fill_template(
            _TRANSLATE_PROMPT,
            {
                "source_language": request.source_language,
                "target_language": request.target_language,
                "text": request.text,
            },
        )
        raw = await self._call_ollama(prompt)
        if "translatedText" not in raw:
            raise AIProviderValidationError(
                "Ollama response missing 'translatedText' key"
            )
        return TranslationResult(translatedText=str(raw["translatedText"]))

    async def translate_question(
        self, request: QuestionTranslationRequest
    ) -> QuestionTranslationResult:
        prompt = _fill_template(
            _TRANSLATE_QUESTION_PROMPT,
            {
                "question_key": request.question_key,
                "field_type": request.field_type,
                "source_language": request.source_language,
                "target_language": request.target_language,
                "text": request.text,
                "help_text": request.help_text or "null",
                "placeholder": request.placeholder or "null",
            },
        )
        raw = await self._call_ollama(prompt)
        text = raw.get("text")
        if not text:
            raise AIProviderValidationError("Ollama response missing 'text' key")
        return QuestionTranslationResult(
            text=str(text),
            helpText=raw.get("helpText") if raw.get("helpText") != "null" else None,
            placeholder=raw.get("placeholder")
            if raw.get("placeholder") != "null"
            else None,
        )

    async def generate_question(
        self, request: QuestionGenerationRequest
    ) -> QuestionGenerationResult:
        prompt = _fill_template(
            _GENERATE_QUESTION_PROMPT,
            {
                "question_key": request.question_key,
                "field_type": request.field_type,
                "purpose": request.purpose,
                "required": str(request.required),
                "target_language": request.target_language,
                "field_config": json.dumps(request.field_config),
            },
        )
        raw = await self._call_ollama(prompt)
        text = raw.get("text")
        if not text:
            raise AIProviderValidationError("Ollama response missing 'text' key")
        return QuestionGenerationResult(
            text=str(text),
            helpText=raw.get("helpText") if raw.get("helpText") != "null" else None,
            placeholder=raw.get("placeholder")
            if raw.get("placeholder") != "null"
            else None,
        )

    async def health_check(self) -> bool:
        """Return True if Ollama is reachable and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=5.0)) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code != 200:
                    return False
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return any(self._model in m for m in models)
        except Exception:
            return False
