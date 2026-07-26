# ADR 0010 — Dynamic Field Detection

**Status:** Accepted
**Phase:** 11 — Dynamic Field Detection
**Date:** 2026-07-26

---

## Context

Phase 9 routes unmatched digital PDFs to `next_step: dynamic_field_detection` and scanned PDFs through Phase 10's OCR; neither phase infers form fields. Phase 11 must turn native text/coordinates, AcroForm widget metadata, and Phase 10 OCR output into candidate form fields — without ever filling in or exporting an unknown document automatically, and without inventing information the source material doesn't actually contain.

---

## Decisions

### 1. Detection results require mandatory user review

Every candidate produced by `MockFieldDetectionProvider` or `LocalFieldDetectionProvider` starts as `review_status: pending_review`. `question_bridge.py` will only ever turn a `confirmed` field into a question — a `pending_review` or `rejected` candidate never does. This follows directly from the domain rule "never invent information": a heuristic guess about a field's label or type is evidence, not a fact, until a human confirms it. `DELETE` on a candidate marks it `rejected` rather than destroying the row, so the review history — including what the system originally guessed — survives.

### 2. Native text, OCR, and AcroForm all normalize into one input shape

`DetectionDocumentInput`/`DetectionPageInput`/`DetectionToken` (in `providers/base.py`) describe evidence uniformly regardless of where it came from — `extraction.py`'s `extract_native_document_input` (PyMuPDF word tokens + AcroForm widgets, PDF point space) and `extract_ocr_document_input` (Phase 10 `OCRResult`, rendered-image pixel space) both produce it. Every token records its own `source` (`native | ocr | acroform`), so downstream code never has to special-case where a piece of text came from, and coordinate spaces are never silently mixed — a document takes exactly one path (native+AcroForm, or OCR), matching how Phase 9/10 already routed it.

### 3. Deterministic local heuristics come before any AI

`LocalFieldDetectionProvider` uses only geometry (line clustering, left-of/above proximity) and keyword/regex matching (`classification.py`) — no model call. This matches "deterministic validation over AI": field detection from layout and known patterns (colon-terminated labels, email/phone/currency value shapes, AcroForm widget types) doesn't require language understanding, so plain code handles it. A future AI-assisted provider remains possible behind the same `FieldDetectionProvider` protocol, but nothing in this phase depends on one — `MockFieldDetectionProvider` covers the entire automated test suite already.

### 4. Confidence is stored only when the provider actually produced one

Every `DetectedFieldCandidate.confidence` traces back to concrete evidence the provider found (an AcroForm widget's own declared type, a label match, a value-pattern match) — `classification.acroform_widget_confidence` and the text-line heuristics in `providers/local.py` compute confidence from what was actually found nearby, never a value invented for its own sake. `normalization.downgrade_low_confidence` enforces the flip side: below `LOW_CONFIDENCE_THRESHOLD` (0.4), a candidate's `field_type` is forced to `unknown` regardless of what was guessed, so weak evidence can never masquerade as a specific type.

### 5. A detected "existing value" is evidence, never an answer

`DetectedField.existing_value` (e.g., text following a label's colon) is surfaced to the user for context only. It is not copied into any `FormAnswer`, and `question_bridge.py` never reads it when materializing questions — the user must type or confirm their own answer through the normal guided-session flow, identical to how OCR text is never auto-treated as a form value.

### 6. Confirmed fields produce temporary, real guided-session questions — not a parallel workflow

`question_bridge.create_session_from_confirmed_fields` materializes confirmed candidates into a synthetic, published `FormTemplate`/`FormVersion`/`FormField` set (keyed `dynamic-doc-{document_public_id}`), reusing `FormService`'s own validation (choice fields need options, a source-language label is required, published versions are immutable) rather than reimplementing any of it. `SessionService.create_session` — completely unmodified — then starts a real guided session. This means Phase 11 adds zero new session/answer state machinery; every existing guarantee about sessions, answers, and PDF export continues to hold for these dynamically-generated forms exactly as it does for predefined ones.

### 7. Filling the original, unknown PDF is explicitly deferred

Detected fields carry geometry (`label_bounding_box`, `input_bounding_box`) but Phase 11 never writes back into the source document. Coordinate-to-PDF mapping for arbitrary, previously-unseen documents is a materially harder and riskier problem than mapping onto pre-audited templates (ADR 0007's explicit, human-reviewed field mappings) — attempting it now would trade a reviewed guess for an unreviewed one at the point that matters most (the actual output file). This is intentionally out of scope until a future phase can address it with the same rigor Phase 8 applied to known templates.

### 8. Cloud AI remains optional and deferred

`FieldDetectionProvider` is a protocol specifically so a cloud-backed implementation could exist later, but nothing in this phase requires one, and the automated test suite must never call one. `LocalFieldDetectionProvider` demonstrates the entire pipeline works without it; if a future phase needs stronger semantic understanding for cases these heuristics can't cover, it plugs in as a new provider, not a rewrite of the service/API/persistence layers.

---

## Consequences

### Positive

- The provider/extraction split means the full request → extract → detect → persist pipeline is tested end-to-end (real PyMuPDF extraction + deterministic mock or local provider) without any AI dependency in CI.
- Reusing `FormService`/`SessionService` unmodified means Phase 11 cannot regress Phases 2, 4, 7, or 8 — it only ever calls their existing, already-tested public methods.
- The mandatory-review model means a wrong heuristic guess costs the user one click to correct or reject, never a silently wrong answer.

### Negative / Trade-offs

- `LocalFieldDetectionProvider` doesn't yet extract AcroForm choice-widget (ComboBox/ListBox) option values, so `select`-type candidates from those widgets currently have no options and downgrade to a plain text question — a known, documented gap rather than a silent one.
- Each confirmed-fields session generates a new `FormVersion` (matching the "published versions are immutable" invariant) rather than reusing one across repeated attempts; this is correct but means re-confirming a document's fields after edits accumulates additional versions under the same synthetic template.
- Text-only (non-AcroForm) candidates have no confirmed `input_bounding_box` — only a label position — since locating an actual blank/input area from text tokens alone isn't attempted in this phase.

---

## Related

- [backend/app/field_detection/](../../backend/app/field_detection/)
- [backend/tests/field_detection/](../../backend/tests/field_detection/)
- [docs/field-detection.md](../field-detection.md)
- [ADR 0007 — Explicit PDF Template Mapping and Secure Export](0007-explicit-pdf-template-mapping.md) (why unknown-PDF filling stays deferred)
- [ADR 0008 — Structural PDF Document Analysis](0008-structural-pdf-document-analysis.md)
- [ADR 0009 — Local OCR Provider](0009-local-ocr-provider.md) (same provider-abstraction pattern; OCR pixel-space input)
