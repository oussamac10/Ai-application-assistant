# AI Form Assistant - Claude Instructions

Read only the imported files relevant to the current task. Do not scan the entire repository unless required.

@docs/claude/project-overview.md
@docs/claude/current-phase.md
@docs/claude/architecture-map.md
@docs/claude/commands.md
@docs/claude/working-rules.md
@docs/claude/domain-rules.md
@docs/claude/session-handoff.md

## Startup

1. Run `git status --short --branch`.
2. Read root `TODO.md`.
3. Confirm the branch matches `current-phase.md`.
4. Inspect the smallest relevant set of files.
5. Give a concise plan before editing.
6. Do not repeat completed phases.

## Completion

1. Run checks relevant to changed files.
2. Run affected regression tests.
3. Update `TODO.md` with exact results.
4. Update `session-handoff.md`.
5. Summarize changes, tests, and blockers.
6. Never claim an unexecuted check passed.

## Efficiency

- Prefer targeted `rg`, `find`, and direct reads.
- Do not repeatedly read unchanged docs.
- Do not paste long files into responses.
- Reuse existing patterns before adding abstractions.
- Keep implementation commentary short.
