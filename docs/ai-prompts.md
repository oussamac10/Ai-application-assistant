# AI Prompting & Guardrails

All AI interactions in `backend/app/ai/` follow strict privacy, determinism, and anti-hallucination rules:

1. **Deterministic Code First**: Dates, emails, phone numbers, booleans, choice selections, IBANs, and required checks are validated deterministically in `backend/app/validation/` without calling an LLM.
2. **Minimal Scoped Context**: Prompts receive only the single active field's metadata, allowed options, language codes (`userLanguage`, `sourceLanguage`, `outputLanguage`), and the user's untrusted answer wrapped in explicit `<user_input>` delimiters — never the full session, unrelated answers, tokens, or secrets.
3. **Structured Pydantic-Validated JSON**: Providers (`MockAIProvider`, `OllamaAIProvider`, `GeminiAIProvider` / Vertex AI) return strict JSON schemas validated by Pydantic. Malformed responses degrade safely to clarification or deterministic fallback.
4. **Never Invent Missing Data**: Ambiguous free-text answers (e.g., `"around 1800"` without currency or period) return `requiresClarification = true` with explicit `uncertainties` rather than guessing values.
5. **Catalog-First Question Resolution**: Approved `question_definitions` and `question_translations` are checked by semantic `question_key` before invoking translation or AI generation.

## Canonical References

- [AI Pipeline, Prompt Architecture & Evaluation (`AI_PIPELINE.md`)](AI_PIPELINE.md)
- [AI Provider Abstraction](ai-provider.md)
- [Reusable Question Catalog](question-catalog.md)
