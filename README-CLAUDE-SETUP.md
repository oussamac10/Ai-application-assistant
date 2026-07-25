# Claude Context Pack for AI Form Assistant

Copy this pack into the repository root.

## Files

- `CLAUDE.md`: small instructions loaded for every project session
- `docs/claude/project-overview.md`: stable project purpose and roadmap
- `docs/claude/current-phase.md`: only the active phase
- `docs/claude/architecture-map.md`: codebase navigation
- `docs/claude/commands.md`: exact commands
- `docs/claude/working-rules.md`: implementation and security rules
- `docs/claude/session-handoff.md`: short continuation state
- `.claude/settings.json`: conservative permissions
- `prompts/start-session.md`: prompt for a fresh session
- `prompts/finish-session.md`: prompt to close a session

## Token-saving rules

1. Keep `CLAUDE.md` short.
2. Keep historical phase details under `docs/progress/`.
3. Keep only current work in `current-phase.md`.
4. Replace, rather than endlessly append to, `session-handoff.md`.
5. Never paste the whole repository into chat.
6. Ask Claude to inspect only relevant files.
7. Run targeted tests while developing and the full suite at phase completion.
