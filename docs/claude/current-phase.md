# Current Phase

## Phase

Phase 14 - Azure Document Intelligence Provider

## Branch

`feature/azure-document-intelligence`

## Base

`feature/automatic-upload-to-questions`

## Objective

Add Azure Document Intelligence as a **second, opt-in** field-detection provider alongside the
existing local rules-based detector, and prove that Azure's output can be converted into the app's
existing internal detected-field format. The local provider stays the default and is not replaced.

Hybrid/fallback behavior between providers is explicitly **Phase 15**, not this phase.

## Reuse

- `FieldDetectionProvider` protocol (Phase 11) — Azure implements the same contract, unmodified
- Phase 13 deterministic confidence routing (`app/field_detection/confidence.py`) — Azure's own
  confidence is only one *input*; it never decides usability, thresholds, or auth
- Phase 13 shared text-line detection passes (`providers/local.py`) — Azure words are converted to
  `DetectionToken`s and run through the same German blank-run / section-context / inline-blank
  logic, so all of Phase 13's quality work applies to Azure output too
- `PrepareQuestionsService` orchestration, ownership checks, question bridge — all unchanged

## In scope

- `AZURE_DOCUMENT_INTELLIGENCE_*` backend-only configuration + validation (fail fast only when
  Azure is the selected provider)
- `FIELD_DETECTION_PROVIDER=azure` in the provider factory (mock | local | azure — no hybrid)
- `AzureDocumentIntelligenceProvider`: submit PDF, poll the async operation, bounded
  timeout/retries, safe error mapping, provider request-id capture
- Deterministic Azure→internal normalization: polygon→bounding-box (inch/pixel/normalized units,
  page rotation, multiple/missing polygons), key-value pairs, selection marks, words→tokens
- Safe Azure error codes mapped to generic user-facing messages
- Provider usage/cost metadata persistence (+ migration)
- Detection-result caching keyed on document checksum + provider + model + analysis version, so a
  repeated request never re-calls Azure and never duplicates fields or questions
- Mocked backend tests (no real Azure calls), ADR 0013, phase + setup documentation

## Out of scope

- Phase 15 hybrid/fallback between providers
- Subscription billing / quota enforcement (only usage metadata is recorded)
- Any frontend flow change — the normal user UI stays provider-agnostic
- Lowering any existing confidence threshold

## Known blocker

No Azure credentials are available in this environment, so the **live-service** manual verification
(requirement 12/16: the exact German rental-contract PDF processed by the real Azure endpoint)
cannot be executed here. Everything else is implemented and verified against a recorded-shape
Azure `prebuilt-layout` response derived from that same PDF, driven through the real orchestration
pipeline end-to-end. See `docs/phases/phase-14-azure-document-intelligence.md` for the exact
manual steps to run once credentials exist.

## Status

In progress.
