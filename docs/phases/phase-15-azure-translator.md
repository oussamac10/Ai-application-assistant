# Phase 15 — Azure Translator Integration

Extracts the `TranslationProvider` abstraction that `docs/claude/domain-rules.md` has always
required, and implements Azure Translator behind it. Full rationale in
[ADR 0015](../decisions/0015-translation-provider-and-azure-translator.md).

## What changed

```
TranslationProvider                       app/translation/base.py
├── MockTranslationProvider               app/translation/providers/mock.py
├── OllamaTranslationProvider             app/translation/providers/ollama.py
└── AzureTranslatorProvider               app/translation/providers/azure.py

app/translation/factory.py     provider selection (mock | ollama | azure)
app/translation/service.py     the pipeline: protect -> dedup -> catalog -> cache -> provider
app/translation/protected.py   deterministic identifier detection
app/translation/backfill.py    fills deferred languages on demand
app/translation/errors.py      safe internal error codes
```

`AIProvider` keeps every non-translation responsibility unchanged.

## Resolution order

Each step exists to *avoid* a provider call:

1. Protected text (identifiers) — never sent anywhere
2. Deduplicate
3. Approved catalog translations
4. Persisted (pending) catalog translations
5. Process cache
6. Primary provider — one array request for everything still unresolved
7. Fallback provider — only the ids the primary did not return
8. Source text — anything still missing

## Configuration

```bash
TRANSLATION_PROVIDER=azure          # mock | ollama | azure
TRANSLATION_FALLBACK_PROVIDER=ollama  # or "none"; must differ from the primary

AZURE_TRANSLATOR_ENABLED=true
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_API_KEY=<key>        # git-ignored root .env only
AZURE_TRANSLATOR_REGION=<region>      # required for a regional resource
AZURE_TRANSLATOR_API_VERSION=3.0
AZURE_TRANSLATOR_TIMEOUT_SECONDS=30
AZURE_TRANSLATOR_MAX_RETRIES=1
AZURE_TRANSLATOR_MAX_BATCH_SIZE=50
```

Validated (fail fast) only when Azure is the selected or fallback provider, so a developer with no
Azure account can still boot.

## Source-language detection

Requests omit `from`, so Azure detects the source language and reports it per element. The detected
language becomes the generated form version's `source_language`, so the original label text is
stored under the language it is actually written in.

This fixes a real defect, not just a cost: field detection performs no language detection, so every
version previously claimed `en`. A German document viewed in an English interface was therefore
never translated — the interface language matched the assumption, so the pipeline concluded there
was nothing to do.

`OllamaTranslationProvider` cannot detect and says so, reporting the assumed language rather than
guessing, and short-circuiting when that assumption makes source and target equal.

## Eager vs deferred languages

Only the **interface** language is translated during preparation. Other supported languages get
source-text placeholder rows — `publish_version` requires a row for every supported language — and
`backfill.py` replaces them when the summary is first requested. It is idempotent and never
overwrites a real translation.

Choice-option **values** are never translated in any path; only their display labels are.

## Diagnostics

Counts, durations and language codes only — never text, labels, option values or credentials:

```
Question generation result: document=... questions=24 skipped=0 version=published
    supported_output_languages=de,en source_language=en eager_language=en
    deferred_languages=de translation_duration=0.04s provider=ollama unique_texts=28
    protected_skipped=0 catalog_hits=0 persisted_hits=0 cache_hits=0 provider_calls=1
    fallback_calls=0 characters=0 provider_latency=0.00s detected_source=en untranslated=0
prepare-questions timing: ... detection_duration=4.80s question_resolution_duration=0.39s
    total_duration=5.20s status=ready questions=24
```

## Benchmark

German rental contract, fresh upload, through the Next proxy,
`FIELD_DETECTION_PROVIDER=azure` + `TRANSLATION_PROVIDER=ollama`:

| | Phase 14 | Phase 15 | Target |
|---|---|---|---|
| `total_duration` | 43.80 s | **5.20 s** | < 15 s |
| `translation_duration` | 34.27 s | **0.04 s** | < 3 s |
| provider calls | 4 | **0** | — |
| generated questions | 24 | 24 | 24 |
| repeat request | 0.09 s, 0 calls | **0.05 s, 0 calls** | 0 calls |

First question still `vermieter_name` / "Vermieter – Name".

## Known limitations

- **The live Azure Translator path is unverified.** No `AZURE_TRANSLATOR_API_KEY` is provisioned,
  so all Azure tests are mocked and the benchmark ran on Ollama. The mocked tests cover the wire
  contract thoroughly, but a live run is required before claiming the provider works end to end.
- With Ollama selected, a German document in an English interface is still not translated — the
  local model cannot detect a source language. Only Azure resolves this.
- **Arabic field detection is weak**: `arabic_test_form.pdf` produced 2 fields from 27 raw
  candidates, with three separate labels merged into one. That is a Phase 13/14 detection concern
  (blank-run and section heuristics are tuned for LTR layout), untouched here. Arabic text itself
  round-trips without corruption and RTL rendering is unchanged.
- The translation cache is process-local and dropped on restart.
