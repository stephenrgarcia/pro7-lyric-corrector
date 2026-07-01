---
name: ProPresenter Lyric Corrector
---

# Continue Rules

Use `AGENTS.md` as the canonical project guide. Read it before changing files,
then follow the linked `README.md`, `docs/ARCHITECTURE.md`, and
`docs/ROUTINE.md` guidance as relevant.

Quick invariants:
- Pure Python standard library only; use Python 3 (`/usr/bin/python3` on macOS; `py`/`python` on Windows).
- Never add a pip dependency.
- Run `python3 tests/run_tests.py` after code, parser, rules, or write-path changes.
- Edit ProPresenter RTF leaves only, never stale sibling plain-text fields.
- Scope writes to the Songs library and fail closed while ProPresenter is open.
- Preserve backups, in-place atomic writes, structural verification, and
  fail-soft `EDIT-LOG.md` logging.
- For the optional lyric AI pass, follow `docs/ROUTINE.md` exactly.
