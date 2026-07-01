# Agent Instructions

Use `AGENTS.md` as the canonical project guide. This singular filename exists
for assistants that look for `AGENT.md` instead of `AGENTS.md`.

Quick invariants:
- Pure Python standard library only; use `/usr/bin/python3`.
- Never add a pip dependency.
- Run `python3 tests/run_tests.py` after code, parser, rules, or write-path changes.
- Edit ProPresenter RTF leaves only, never stale sibling plain-text fields.
- Scope writes to the Songs library and fail closed while ProPresenter is open.
- For the optional lyric AI pass, follow `docs/ROUTINE.md` exactly.
