# Q&A Workflow and Transitions

This document outlines the state transitions and workflow logic of the form assistant's question and answer cycles.

## Field Selection Rule

When a user requests the "current field" or proceeds forward, the backend calculates the next active field using the following deterministic search:
1. Fetch all fields belonging to the session's active form version, ordered by their `position`.
2. Iterate through the fields:
   - Identify the first field that is `required` and does *not* have a corresponding `FormAnswer` with status `confirmed`.
3. If all required fields are confirmed, fall back to the stored `current_field_position` or the final field of the form.

## Answer Lifecycle Transitions

```mermaid
state_diagram
    [*] --> unanswered
    unanswered --> needs_clarification : submit_answer (missing info)
    unanswered --> awaiting_confirmation : submit_answer (valid & full)
    unanswered --> draft : submit_answer (invalid value)

    needs_clarification --> needs_clarification : submit_clarification (still missing)
    needs_clarification --> awaiting_confirmation : submit_clarification (info provided)
    needs_clarification --> draft : submit_clarification (invalid value)

    draft --> awaiting_confirmation : edit_answer (fixes issues)
    awaiting_confirmation --> confirmed : confirm_answer
    confirmed --> awaiting_confirmation : edit_answer (resets confirmation)
```

### 1. Submit Answer
- Submits `original_answer`.
- Calls Mock AI Extraction.
- If missing money variables -> `needs_clarification`.
- Run normalizer and validator. If valid -> `awaiting_confirmation`. Otherwise -> `draft`.

### 2. Submit Clarification
- Submits key-value pairs (e.g. `currency: "EUR"`).
- Merges with existing normalized values.
- Re-evaluates. Once complete and valid, transitions to `awaiting_confirmation`.

### 3. Confirm Answer
- User reviews the extracted information.
- Confirms details. The answer transitions to `confirmed` and the backend advances the session position to the next field.

### 4. Edit Answer
- The user can edit any previous field.
- If the answer was `confirmed`, the confirmation is cleared (`confirmed_by_user = False`), and progress is recalculated.

## Session Summary & Final Confirmation

- `GET /api/form-sessions/{session_id}/summary` lists all fields and their answers.
- `POST /api/form-sessions/{session_id}/confirm-summary`:
  - Enforces that all required fields are `confirmed`.
  - Ensures no answers are `invalid` or `needs_clarification`.
  - Transitions the session from `in_progress` to `awaiting_final_confirmation` and then immediately to `ready_for_export`.
