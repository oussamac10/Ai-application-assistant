# ADR 0003: Deterministic Q&A Workflow and Mock AI Provider

## Status

Approved

## Context

For MVP Phase 4, the application must support a multilingual, structured question and answer workflow. This workflow takes original answers, extracts key properties via the AI Provider (mocked), deterministically normalizes and validates them, manages clarification/confirmation statuses, tracks completion progress, and supports navigation.

## Decision

We chose to implement the Q&A workflow with the following specifications:
1. **Answer Storage**: A new table `form_answers` holds answer status, validation status, translation status, original answers, normalized JSONB values, and translations. A database-level unique constraint on `(session_id, field_id)` prevents duplicates.
2. **Deterministic Rules**: We implemented normalizers and validators in `app/answers/normalization` and `app/answers/validation` for all 14 field types.
3. **Mock AI Provider**: A `MockAIProvider` simulates LLM behavior locally. If the user answers a money field with digits alone, it triggers clarification requesting `currency` and `period`.
4. **Navigation and Edits**: Navigating back via `previous-field` preserves answers. Overwriting a confirmed answer resets its confirmation status and dynamically recalculates completion progress.
5. **Final Session Transition**: The `confirm-summary` endpoint validates that all required fields are confirmed, then transitions the session through `awaiting_final_confirmation` to the terminal state `ready_for_export`.

## Consequences

- The workflow is robust, deterministic, and doesn't rely on expensive or non-deterministic external LLMs.
- Progress calculations are dynamic and accurate.
- Anonymous sessions have strong, cryptographically verified integrity during mutations.
