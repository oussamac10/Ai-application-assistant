"""OllamaAIProvider — calls a local Ollama instance for AI operations.

Design rules (see docs/ai-provider.md):
- All requests use stream=false and format="json".
- Responses are validated with Pydantic before use.
- Timeouts and retries are bounded.
- No sensitive content (answers, tokens, secrets) is ever logged.
- Prompt templates are loaded from the prompts/ directory at import time.
- The backend must reach Ollama via OLLAMA_BASE_URL (host.docker.internal in Docker).
- Prompt injection: user-supplied text is embedded only as a value in a
  structured JSON payload and is marked as untrusted in the prompt template.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

import httpx

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

    async def _call_ollama(self, prompt: str) -> dict[str, Any]:
        """POST to Ollama /api/generate with retries and safe error mapping.

        The prompt text is sent as-is.  Sensitive answer contents are already
        embedded in the prompt by the caller and are NOT logged here.
        """
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

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
                response_text: str = raw.get("response", "")
                try:
                    parsed: dict[str, Any] = json.loads(response_text)
                    return parsed
                except (json.JSONDecodeError, ValueError) as exc:
                    raise AIProviderMalformedResponseError(
                        "Ollama returned non-JSON content"
                    ) from exc

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Ollama timeout on attempt %d/%d",
                    attempt + 1,
                    self._max_retries + 1,
                )
            except httpx.ConnectError as exc:
                raise AIProviderUnavailableError(
                    "Cannot connect to Ollama service"
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise AIProviderUnavailableError(
                    f"Ollama returned HTTP {exc.response.status_code}"
                ) from exc
            except AIProviderMalformedResponseError:
                raise
            except Exception as exc:
                raise AIProviderUnavailableError(
                    "Unexpected error communicating with Ollama"
                ) from exc

        raise AIProviderTimeoutError(
            f"Ollama did not respond after {self._max_retries + 1} attempt(s)"
        ) from last_error

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
        raw = await self._call_ollama(prompt)
        return ExtractionResult(
            normalizedValue=raw.get("normalizedValue"),
            outputValue=raw.get("outputValue"),
            requiresClarification=bool(raw.get("requiresClarification", False)),
            uncertainties=list(raw.get("uncertainties", [])),
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
