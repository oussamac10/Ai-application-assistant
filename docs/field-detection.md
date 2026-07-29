# Dynamic Field Detection — User Guide

**Phase:** 11
**Feature:** Dynamic Field Detection

---

## Overview

When Phase 9's document analysis finds a digital PDF that doesn't match any predefined template (`next_step: dynamic_field_detection`), or once Phase 10's OCR completes on a scanned document, the AI Form Assistant can scan it for likely form fields — labels, input areas, checkboxes, choices, and more — so you can review and correct them before answering any questions.

Detection is a starting point, not an authority: **every candidate field must be reviewed before it becomes a question.** Nothing is filled in or exported automatically.

---

## How to use it

### Step 1 — Reach the detect-fields page

- For an unmatched digital PDF: after upload analysis, click **Detect Fields**.
- For a scanned PDF: after [OCR](ocr.md) completes, click **Detect Fields**.

A document that matches a known supported template skips this entirely and uses the existing guided form directly.

### Step 2 — Start detection

Click **Start Detection**. The document is scanned using its native text and layout (for digital PDFs) or its OCR text and coordinates (for scanned PDFs), plus any interactive AcroForm fields it already has. Re-visiting this page for a document that already completed detection shows the same result without re-processing it.

### Step 3 — Review candidate fields

Detected fields are listed grouped by page. For each one you can see:

- The detected **label** and **field type** — both editable
- A **confidence** score; anything below the low-confidence threshold is flagged for extra scrutiny and defaults to an "unknown" type rather than a guessed one
- **Confirm** or **Reject** buttons

Use **Confirm all high-confidence fields** to quickly accept everything the system is reasonably sure about, then handle the flagged ones individually.

### Step 4 — Create questions

Once at least one field is confirmed, choose the language the completed form should be written in and click **Create Questions**. This starts the same guided question-and-answer workflow used elsewhere in the app — only confirmed fields ever become questions; pending or rejected candidates never do.

---

## What gets detected

Field types: text, long text, date, email, phone, address, number, currency amount, checkbox, single choice (radio or dropdown), signature, or unknown.

For AcroForm-based documents, the interactive field's own type is authoritative (a checkbox widget is detected as a checkbox). For plain text or OCR-derived documents, a line of text ending in a colon (e.g. "Email:") is treated as a label candidate, and its type is guessed from the label wording and, if present, from the value written after the colon.

Any value found near a detected field is shown for your information only — it is never automatically treated as your answer.

---

## Security and privacy

- Detection runs entirely on the server; no document content is sent to a third party.
- Detection results inherit the same private storage, ownership-token, and expiration model as the source document.
- Only the holder of the document's ownership token can request, view, or edit a detection result.
- No internal storage paths are ever exposed in API responses.

---

## Troubleshooting

### "This document does not require field detection"

The document was already classified as a supported template or doesn't need this step.

### "This document matches a supported template; use the guided form instead"

Predefined templates skip detection entirely — start the guided form directly from the upload result.

### "OCR must complete before field detection can run"

Run OCR on the scanned document first, then return to this page.

### "Field detection is already in progress for this document"

Wait for the current detection run to finish before starting a new one.

---

## Phase 13: automatic use for normal users

As of Phase 13, normal users never see this manual review screen. Uploading a document calls
`POST /api/source-documents/{id}/prepare-questions`, which analyzes, runs OCR (only if needed),
runs detection, applies deterministic confidence routing (`app/field_detection/confidence.py`),
generates questions from what's safe to use automatically, and starts the guided session — all in
one idempotent call. See [Phase 13 — Automatic Upload-to-Questions Flow](phases/phase-13-automatic-upload-to-questions.md)
and [ADR 0012](decisions/0012-automatic-confidence-routing.md) for the full behavior.

This page (and the manual confirm/reject/create-questions endpoints described above) remains
fully functional, unchanged, for admin/development/debug use — reachable directly at
`/application/document/{id}/detect-fields`, and linked from the upload flow only when
`NEXT_PUBLIC_ENABLE_DETECTION_DEBUG_UI=true` or (outside production) a `?debug=1` query param.

## Recognizing input areas that are not AcroForm widgets

Most real-world public-sector forms are Word exports with no interactive fields at all. The local
provider recognizes the ways such forms mark a fillable area, all deterministically:

| Pattern | Example | How it is recognized |
|---|---|---|
| Colon label + blank run on one line | `Name:` … `…………………` | colon, plus a blank-run sibling segment on the same physical line |
| Blank run in the same segment | `IBAN ________________` | `classification.is_blank_run` on a token within the segment |
| Label above a blank line | `IBAN` / `________` stacked | lone label whose next close-below line is only a blank run |
| Sentence-embedded blank | `beginnt am ____ und endet am ____` | an unusually wide inter-word gap (`geometry.INLINE_BLANK_GAP_RATIO`) **plus** an explicit German trigger word beside it |
| Large blank area below a label | `Sonstige Vereinbarungen:` + gap | `geometry.is_large_vertical_gap` → `multiline_text` |

A "blank run" is any run of 3+ dots, Unicode ellipses (`…`), middle dots (`·`), underscores, or
hyphens. A blank run is treated strictly as a *placeholder*: it is never stored as the field's
`existing_value`, so the guided flow never shows dots as a pre-filled answer to confirm.

Sentence-embedded blanks deserve special note, because a wide gap alone is not evidence. Measured
on real German forms, ordinary word spacing sits at ~0.2× line height — including inside long
justified legal paragraphs — while a deliberate blank measures ~2.1–2.6×. The threshold sits well
between the two, **and** a trigger word must sit directly beside the gap (`am`/`der`/`datum` before
it → date; `Euro`/`EUR`/`€` after it → currency; `Personen`/`Zimmer` after it → integer). Both
signals are required, so legal prose never produces a field.

## Section context and repeated labels

German contracts reuse the same short label under different parties: `Name:`, `Straße, Nr.` and
`PLZ, Ort` each appear once under "Zwischen dem Vermieter" (landlord) and again under "und dem
Mieter" (tenant). Since deduplication keys on `normalized_name`, a section prefix is required or
the second occurrence of each is silently dropped and the user is only ever asked about one party.

`app/field_detection/sections.py` tracks the active context while scanning each page and prefixes
every candidate's stable key with it (`vermieter_name`, `mieter_name`). For *party* contexts the
user-visible label is prefixed too ("Vermieter – Name"), since "Name" twice would be ambiguous in
the guided flow; for `§ N Titel` sections only the key is prefixed, because "Mietkosten – IBAN"
tells the user nothing that "IBAN" doesn't.

## What is never turned into a field

- `§ N Titel` section headings.
- A segment that is itself, or begins with, a blank run (that is the input area, not a label).
- A label longer than 6 words (prose), or a 3+-word phrase starting in lower case — in German and
  English alike a real label is a capitalized noun phrase or an acronym, whereas a wrapped
  sentence continues in lower case ("wird folgender Mietvertrag geschlossen:").
- Footer/margin metadata (keyword **and** bottom-of-page position both required).
- A choice group named only by a bare connective ("oder"), or whose "options" are complete
  sentences — those are independent alternative statements, and swallowing them as options would
  hide the real fillable fields inside them.

## Related

- [Document Upload and Analysis](document-upload-analysis.md)
- [OCR Integration](ocr.md)
- [ADR 0010 — Dynamic Field Detection](decisions/0010-dynamic-field-detection.md)
- [backend/app/field_detection/](../backend/app/field_detection/)
