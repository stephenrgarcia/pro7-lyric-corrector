# AGENTS.md

Project orientation for AI coding assistants and developers.
This is the canonical repository guide. Tool-specific starter files such as
`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `HERMES.md`, Copilot, Cursor, Cline, Roo,
Continue, Junie, Kiro, Devin, Windsurf, Firebase Studio, and OpenHands adapters
all point back here. Read this file before changing anything.

`pro7_lyric_corrector` — a one-time or always-on ProPresenter 7 worship-lyric
autocorrector for macOS and Windows, scoped to the **Songs** library. Pure
Python 3 standard library, **zero dependencies**.

## Read these first
- `README.md` — user-facing: what it does and how to install it.
- `docs/ARCHITECTURE.md` — how a `.pro` file (binary protobuf with embedded RTF)
  is parsed and edited without corrupting it. Read before touching wire/rtf code.
- `docs/ROUTINE.md` — the optional AI pass. Any assistant should follow this file
  verbatim to make the context-dependent capitalization calls.

## How it's built (two layers)
1. **Deterministic engine** (no AI, no network): scan → gate → correct → back up
   → atomic in-place write → structural verify → log. Drives both `apply-once`
   (one pass) and `watch` (always-on ~5s poll via a macOS LaunchAgent or
   Windows Task Scheduler task).
2. **AI pass** (optional): the deterministic engine *flags* ambiguous casing it
   can't decide; `ai-batch` emits those songs as JSON, an assistant following
   `docs/ROUTINE.md` proposes fixes, and `ai-batch --apply` validates and writes
   them through the same safe pipeline.

## Essentials
- Run tests: `python3 tests/run_tests.py` (no pytest; pure stdlib).
- Use Python 3 (`/usr/bin/python3` on macOS; `py`/`python` on Windows). Never
  add a pip dependency — keep it dependency-free.
- Entry point: `pro7_lyric_corrector.py`. Package: `pro7corrector/`.
- Commands: `discover`, `inspect <file>`, `calibrate` (preview), `review`
  (approve one-by-one before writing), `apply-once`, `watch`, `install-agent`,
  `start`/`stop`/`status`, `ai-batch`, `--restore`.

## File map (pro7corrector/)
- `wire.py` — zero-dependency protobuf wire-format codec (round-trips `.pro`).
- `rtf.py` — RTF extract/splice; run-preserving; cp1252 escapes.
- `presentation.py` — locate the title + lyric RTF leaves; structural verify.
- `rules.py` — all deterministic correction rules and word lists.
- `monitor.py` — the scan/correct/back-up/log engine + the watch loop.
- `song_gate.py` — Songs-only + is-this-actually-a-song gate.
- `backup.py` — timestamped backups + atomic writes.
- `changelog.py` — append every edit to `EDIT-LOG.md` (fail-soft).
- `reviewed.py` — fingerprints lyrics so the AI pass only sees changed songs.
- `aibatch.py` — emit / apply the AI proposals (hard validation on apply).
- `agent.py` — install/start/stop the macOS LaunchAgent or Windows scheduled task.
- `config.py` — cross-platform root/library discovery, paths, ProPresenter-running detection.

## Hard rules (don't regress)
- Edit **RTF leaves only** — ProPresenter renders from the RTF, not the sibling
  plain-text field (which is stale template junk library-wide).
- **Songs library only** — never sermons/announcements/playlists/media/themes.
- Title handling matches protobuf field 3 **by number, not node kind** (a title
  whose bytes look like protobuf re-parses as a message). See
  `presentation._find_title_node`. There's a regression test; don't "simplify".
- Every write: backup → atomic replace **in place** (no new files in the
  library) → re-parse and prove all non-lyric bytes byte-identical → skip on
  doubt. **Fail-closed while ProPresenter is open** (defer, retry later).
- The RTF splice is **run-preserving**: keep formatting control segments
  byte-for-byte; only re-encode text runs.
- Both write paths append to `EDIT-LOG.md` via `changelog.py` — keep it
  **fail-soft**: a logging error must never block or undo a correction.

## Capitalization policy (the nuance lives in rules.py)
- **Always capitalized** (`ALWAYS_CAP`, `PHRASE_RULES`): proper names/titles of
  God — God, Jesus, Lord, Lion, Lamb, King of Kings, Holy Spirit/Ghost/One, etc.
- **Always lowercase mid-line** (`COMMON_WORDS`, `FUNCTION_WORDS`): attributes
  that are never titles (grace, glory, blood, mercy, majesty, kingdom, holy,
  cross) and grammatical function words (a/the/and/in/of/to/is/be…). The first
  word of every line is always capitalized (`_first_word_cap`).
- **Ambiguous → flagged for the AI, never guessed** (`AMBIGUOUS_DIVINE` + the
  flags in `_flag_for_ai`): pronouns that may be God or human (You/Your,
  He/Him/His, Me/My), "the One Who", words that are sometimes a title for Jesus
  (king, spirit, word, name, father, son, rock, shepherd, light, life, way,
  truth, …), and a word-initial single quote that may be an opening quote vs. an
  apostrophe.
- To change behavior: flip a `Config` flag or edit the word lists in `rules.py`;
  re-run `calibrate` to preview, then `review` or `apply-once`. Add a test in
  `tests/run_tests.py`.

## Safety model
Backups go to the user's Documents folder under
`ProPresenter Backups/lyric-corrector/` (with a `manifest.jsonl`), outside the
library; restore via `--restore`. On macOS the always-on agent needs Full Disk
Access granted to `/usr/bin/python3` (it touches `~/Documents`); on Windows it
uses Task Scheduler. Special-glyph payloads and non-songs are skipped, never
mangled.

## AI IDE compatibility files
Keep this file as the source of truth. Compatibility starters should stay short
and point back here so rules do not drift between tools. When adding or changing
project guidance, update `AGENTS.md` first, then only adjust adapters if a tool
needs different front matter or file placement.
