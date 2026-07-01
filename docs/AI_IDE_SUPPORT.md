# AI IDE Support

`AGENTS.md` is the canonical project guide. The other files in this list are
compatibility starters for tools that look in a specific place. Keep those files
short and point them back to `AGENTS.md` so rules do not drift.

## Canonical source

- `AGENTS.md` - shared project rules for agents and developers.

## Root-level starters

- `AGENT.md` - singular fallback for assistants that look for it.
- `CLAUDE.md` - Claude Code.
- `GEMINI.md` - Gemini CLI / Gemini Code Assist workflows.
- `QWEN.md` - Qwen Code.
- `HERMES.md` - Hermes-compatible workflows that scan this filename.
- `CONVENTIONS.md` - convention-file fallback used by some coding assistants.
- `.rules` - generic project-rule fallback.
- `.cursorrules` - legacy Cursor fallback.
- `.windsurfrules` - legacy Windsurf fallback.

## Tool-specific folders

- `.github/copilot-instructions.md` - GitHub Copilot repository instructions.
- `.github/instructions/pro7-lyric-corrector.instructions.md` - VS Code /
  Copilot path-scoped instructions.
- `.cursor/rules/pro7-lyric-corrector.mdc` - Cursor project rule.
- `.windsurf/rules/pro7-lyric-corrector.md` - Windsurf workspace rule.
- `.devin/rules/pro7-lyric-corrector.md` - Devin workspace rule.
- `.clinerules/pro7-lyric-corrector.md` - Cline workspace rule.
- `.roo/rules/pro7-lyric-corrector.md` - Roo Code workspace rule.
- `.continue/rules/pro7-lyric-corrector.md` - Continue workspace rule.
- `.junie/guidelines.md` - JetBrains Junie guidelines.
- `.kiro/steering/pro7-lyric-corrector.md` - Kiro steering.
- `.idx/airules.md` - Firebase Studio / Project IDX AI rules.
- `.openhands/microagents/repo.md` - OpenHands repository microagent.
- `.aider.conf.yml` - Aider config that loads `AGENTS.md`.

## Update policy

When project behavior changes, edit `AGENTS.md` first. Update an adapter only
when a tool needs different front matter, a different path, or a shorter local
summary. The optional worship-lyric AI pass always follows `docs/ROUTINE.md`.

## Windows setup support

The repo was built and tested on macOS. Windows support has been added by an
AI-assisted coding pass and covered with simulated tests, but it has not yet
been field-tested on a real Windows ProPresenter install. If a user hits a
Windows setup issue, have the assistant read `README.md`, `AGENTS.md`, and
`docs/ARCHITECTURE.md`, then debug the local root path, Python launcher,
ProPresenter process check, or Task Scheduler command directly.
