---
name: ai-form-current-phase
description: Continue the active development phase of the AI Form Assistant project without repeating completed work. Use when the user asks to continue, implement, verify, review, or finish the current phase; update the phase TODO; inspect the GitHub repository or a local checkout; run targeted tests; preserve completed phases; and produce a concise handoff. Supports repository work through the GitHub connector when available and local git/files when mounted.
---

# AI Form Assistant Current Phase

## Purpose

Continue the project's active phase from its recorded state, implement the next coherent slice, verify it honestly, and keep the phase TODO and handoff current while minimizing context use.

## Load only what is needed

Read these references as required:

- Project roadmap and strict phase boundaries: `references/roadmap.md`
- Startup, implementation, verification, and handoff workflow: `references/workflow.md`
- Project conventions, security rules, and output format: `references/rules.md`

Do not load all reference files when the task needs only one.

## Resolve repository context

1. Identify the repository from the conversation, connected GitHub context, or local git remote.
2. Prefer a local checkout for code execution and tests when available.
3. Use the GitHub connector for repository files, commits, branches, pull requests, and remote metadata.
4. When both exist, keep the local branch and remote target aligned.
5. If neither local files nor GitHub access is available, explain the exact missing access instead of pretending to inspect code.

## Start the current phase task

1. Read repository instructions first, especially `.agents/AGENTS.md`, `AGENTS.md`, or `CLAUDE.md` when present.
2. Read root `TODO.md` and the short current-phase or handoff file if present.
3. Run or retrieve branch and working-tree status.
4. Confirm the active phase and branch from repository evidence.
5. Inspect only the smallest set of source files needed for the next unchecked task.
6. State a short plan, then perform the work in the current response.

Do not ask the user to repeat information already present in the repository or conversation.

## Continue implementation

- Work only on the current phase.
- Reuse existing services, repositories, models, schemas, components, and error patterns.
- Keep HTTP routes thin and business rules in services.
- Keep database access in repositories when that pattern exists.
- Make migrations reversible.
- Preserve backward compatibility for all completed phases.
- Avoid speculative abstractions and unrelated cleanup.
- Do not introduce features assigned to later roadmap phases.

When the user asks only for an agent prompt or TODO, produce that artifact instead of editing code. When the user asks to continue the phase, inspect and implement code directly when tools permit, and maintain the TODO as part of the work.

## Verify honestly

Run targeted checks first, then the full checks required by the phase or affected subsystem.

- Never mark a criterion complete without evidence.
- Record exact pass, fail, and skip counts.
- Keep failed or unexecuted checks unchecked.
- Verify migration upgrade and downgrade when database schema changes.
- Run regression tests for affected completed phases.
- Do not claim GitHub Actions or local commands ran unless they actually ran.

## Maintain phase state

Update root `TODO.md` with:

- checked items only for verified work
- exact verification results
- remaining blockers or deferred checks
- no historical clutter from older phases

Archive a completed phase under `docs/progress/` before resetting the root TODO for a new phase. Do not start a new phase unless the user requests it or the current phase is fully completed and the repository workflow explicitly requires transition.

## Finish and hand off

End with a compact summary containing:

1. What changed
2. Files or subsystems affected
3. Checks run and exact results
4. Remaining unchecked work or blockers
5. The single next concrete action

Update the repository handoff file when one exists. Keep it short by replacing stale details rather than appending an unlimited history.
