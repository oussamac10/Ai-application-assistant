# Phase S3 Progress: Multilingual Grid-Table Form Ingestion & Azure Layout Normalization

**Date Completed:** 2026-11-01  
**Status:** Verified & Released

## Overview
Administrative and immigration forms (such as the German Residence Permit Application / *Antrag auf Erteilung eines Aufenthaltstitels*) heavily rely on tabular layouts with multiple languages in a single cell (German, English, French, Turkish, Serbo-Croatian). Previously, Azure Document Intelligence classified these as general `tables` rather than `keyValuePairs`, causing key fields (e.g. `2. Familienname`, `3. Vornamen`, `4. Geburtsdatum`) to be missed, while multi-lingual labels produced fragmented sub-tokens (`'/'`, `'en'`, `'(dans'`).

## Key Improvements
1. **Azure Table Form Field Extraction (`extract_table_candidates`)**:
   - Parses `analyzeResult.tables` cells.
   - Pairs label cells in column `c` with blank/input cells in column `c+1` or within the same row.
   - Bounding boxes are accurately mapped for preview and overlays.
2. **Selection Mark Classification**:
   - Azure `:unselected:` and `:selected:` marks are mapped to `checkbox` instead of defaulting to `text`.
3. **Multilingual Label Sanitization**:
   - Filters out degenerate single punctuation and preposition fragments (`'/'`, `'(dans'`, `'und'`, `'en'`).
   - Retains primary language label cleanly.
4. **Verified Reference Form**:
   - `fixtures/pdf/ludwigsburg-aufenthalt-antrag.pdf` was processed live through Azure Document Intelligence.
   - 42 fields detected cleanly with proper types and positions.

## Verification
- `pytest tests/field_detection/` (504 passed, 1 skipped)
- Ruff & Mypy: 0 errors
- Frontend: 30 test files, 252 tests passed
