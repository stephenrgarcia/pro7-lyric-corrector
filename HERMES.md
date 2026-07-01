# Hermes Instructions

Use `AGENTS.md` as the canonical project guide. This file is included for
Hermes-compatible workflows that scan for `HERMES.md`; keep `AGENTS.md` as the
source of truth.

Quick invariants:
- Pure Python standard library only; use Python 3 (`/usr/bin/python3` on macOS; `py`/`python` on Windows).
- Never add a pip dependency.
- Run `python3 tests/run_tests.py` after code, parser, rules, or write-path changes.
- Edit ProPresenter RTF leaves only, never stale sibling plain-text fields.
- Scope writes to the Songs library and fail closed while ProPresenter is open.
- For the optional lyric AI pass, follow `docs/ROUTINE.md` exactly.
