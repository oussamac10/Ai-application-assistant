# ADR 0006: Frontend Guided Form Flow & Session State Management

## Status
Approved

## Context
In MVP Phase 7, the AI Form Assistant requires a guided frontend experience. The application must support:
- Creating anonymous form sessions
- Presenting one field/question at a time
- Providing local translation across three UI languages (English, German, French, Arabic)
- Supporting Right-to-Left (RTL) layout for Arabic
- Confirming, clarifying, and editing answers
- Recalculating progress based on backend updates
- Summarizing responses and finalizing confirmation for export

To secure anonymous sessions, we must ensure that ownership tokens (retrieved when starting a session) are never placed in the URL and are stored safely on the client side.

## Decision
1. **Client-Side Token Storage**:
   - The session ownership token (`ownershipToken`) is stored in `sessionStorage` mapped to the specific `sessionId`.
   - Storing it in `sessionStorage` ensures it is isolated to the specific browser tab and is cleared when the tab is closed.
   - It is never placed in the URL, preventing accidental leakage when copy-pasting the link.
   - The token is sent in the `X-Session-Token` custom header on all subsequent API calls.
2. **Localization & RTL Support**:
   - Client-side localization uses `next-intl` with pre-defined locale files (`en.json`, `de.json`, `fr.json`, `ar.json`).
   - The `LanguageProvider` manages the active language state and persists it to `localStorage`.
   - When the locale is set to `ar` (Arabic), the provider automatically sets `document.documentElement.dir = "rtl"` and `document.documentElement.lang = "ar"`.
3. **Workflow Routing & States**:
   - The frontend is built as a state machine mapping backend-driven statuses:
     - `answering`: Standard question-input screen.
     - `needs_clarification`: Displays a sub-form to request missing fields for money/complex values.
     - `awaiting_confirmation`: Displays the proposed normalization value vs. the original answer for user validation.
     - `submitting`: Disables actions to prevent duplicate requests.
   - The backend acts as the single source of truth for the next question, field order, and progress.
4. **Summary & Export-Ready Transitions**:
   - `/application/session/[sessionId]/summary` lists all form questions and current values.
   - Clicking "Edit" updates/resets confirmation of that field on the backend and redirects the user back to the workflow screen.
   - Finalizing the summary transitions the session to `ready_for_export`, leading to the `/application/session/[sessionId]/complete` page.

## Consequences
- **Secure Sessions**: Anonymous session tokens are kept safe from cross-tab leakage and url-copy sharing.
- **RTL Integrity**: Selecting Arabic changes the layout direction dynamically and beautifully, honoring the CSS rules.
- **Premium Aesthetics**: Fluid CSS gradients, glassmorphism containers, responsive form layouts, and interactive components.
- **Robust User Control**: Clear distinction between original answers and proposed/normalized values, with easy back-and-forth editing.
