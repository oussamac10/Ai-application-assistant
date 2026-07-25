# Current Phase

## Phase

Phase 10 - OCR Integration

## Branch

`feature/ocr-integration`

## Base

`feature/form-upload-analysis`

## Objective

Add local OCR for documents classified by Phase 9 as scanned or OCR-required. Persist normalized page-level OCR results for Phase 11.

## Reuse

- `SourceDocument` ownership and storage
- Phase 9 analysis and next-step result
- private storage and expiration
- existing error contracts and localization patterns

## In scope

- OCR provider interface
- deterministic mock provider
- local OCR provider
- page rendering
- persisted OCR results
- protected OCR API
- frontend OCR status/results
- cleanup, tests, docs, ADR 0009

## Out of scope

- arbitrary field detection
- field inference
- form-definition generation
- cloud OCR
- background workers
- accounts and payments

## Before implementation

Verify deferred Phase 9 checks in root `TODO.md`:
- mypy
- Alembic downgrade and re-upgrade
- Playwright upload flow

## Status

Not started.
