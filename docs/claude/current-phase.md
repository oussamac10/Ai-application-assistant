# Current Phase

## Phase

Phase 15 - Azure Translator Integration

## Branch

`feature/azure-translator`

## Base

`feature/azure-document-intelligence`

## Objective

Introduce the `TranslationProvider` abstraction that `docs/claude/domain-rules.md` already names
but the codebase never had, and implement **Azure Translator** behind it as the provider used for
translating question labels, choice options and other display text.

Translation currently rides on `AIProvider.translate_output` / `translate_output_batch`, which
conflates two unrelated capabilities: language understanding (extraction, clarification, question
generation — genuinely a language-model job) and plain text translation (a dedicated service does
this better, faster and more predictably). This phase separates them.

Azure Translator also fits the batching contract built in Phase 14: its API takes an **array** of
texts per request and returns results in order, so one request replaces a chunked sequence of
local-model generations.

## Reuse

- Phase 14 `app/ai/batch_translation.py` — the dedup / cache / approved-catalog /
  per-item-fallback pipeline is provider-agnostic and stays. Only the call at the bottom changes.
- Phase 14 id-keyed result mapping — Azure returns results positionally, so the adapter must
  convert position to the caller's ids explicitly rather than trusting order end to end.
- Phase 14 Azure provider patterns (`AZURE_*` config validated only when selected, bounded
  timeout/retries, safe error mapping, request-id capture, usage metadata, counts-only
  diagnostics) — same shape here.
- The hybrid question-resolution order in `domain-rules.md` is unchanged: an approved reusable
  question or static translation still wins, and translation is only reached when neither exists.

## Scope (confirmed)

- `TranslationProvider` protocol + factory (`mock | ollama | azure`), with Ollama kept as an
  implementation so nothing regresses when Azure is not configured
- `AZURE_TRANSLATOR_*` backend-only configuration, failing fast only when Azure is selected
- `AzureTranslatorProvider`: array request, bounded timeout/retries, safe error mapping, per-item
  validation, usage/character-count metadata
- Deterministic mock provider; no automated test may call the live service
- ADR, phase doc, `.env.example` / `docker-compose.yml` passthrough
- Manual verification against the German rental contract, reporting before/after duration and
  call counts

Source-language auto-detection was confirmed **in** scope (decision 3): it was Phase 14's largest
remaining source of wasted work, and it is also a correctness fix — a German document viewed in an
English interface was never translated, because the interface language matched the assumed source
language.

## Out of scope

- Replacing `AIProvider` for anything other than translation
- Answer-value translation and output-language rendering changes
- Improving field detection for RTL documents (see the Arabic result in `TODO.md`)
- Background jobs / progress polling (Phase 20)
- Billing or quota enforcement — usage metadata only

## Status

Implemented and verified, with one item explicitly blocked.

Built: `TranslationProvider` + factory (mock/Ollama/Azure), `AzureTranslatorProvider` with
positional→id mapping and per-item validation, `AZURE_TRANSLATOR_*` configuration validated only
when Azure is selected, deterministic identifier protection, source-language detection recorded on
the generated version, eager interface language with deferred output-language backfill, safe
provider→fallback→source-text degradation, and counts-only diagnostics.

Measured on the German rental contract: `total_duration` 43.80 s → **5.20 s**,
`translation_duration` 34.27 s → **0.04 s**, 24 questions unchanged, repeat request 0.05 s with
zero provider calls. Backend 574 passed, ruff/mypy clean; frontend 129 passed, lint/typecheck
clean.

**Blocked:** the live Azure Translator path is unverified — no `AZURE_TRANSLATOR_API_KEY` is
provisioned, so all Azure tests are mocked and the benchmark ran on Ollama. See `TODO.md` →
"Blocked" for the exact steps to close it.
