# Pstack alongside Matt Pocock

<!-- portable-engineering-skills:v1 -->

Lauren Tan (Poteto)'s canonical [pstack](https://github.com/cursor/plugins/tree/0b8e952052d482ee6de06deebf14d590d77b1b34/pstack), version **0.15.26**, pinned on 2026-10-18. The original Cursor source includes an official Claude Code adapter. [SOURCE.json](SOURCE.json) records all 171 source hashes and the 55 main skills (31 workflow/support + 24 principles).

## Start here

For coding work, read this repository's [combined engineering guide](../../docs/agent-engineering.md). It selects Matt's shaping/specification and acceptance workflow, pstack investigations and verification, and one execution coordinator for a bounded phase. Applicable repository instructions control scope, quality checks, release and authorization. Existing teaching rules apply where a course exists.

`entrypoints/` exposes all main pstack skills with `pstack-` names and a [portable harness adapter](AIOS-ADAPTER.md). Matt's same-named skills retain their identity. Every entrypoint loads the adapter before its original source. These are available workflows; installation does not start an unattended mode.

## Repository-contained installation

This repository carries its own `skills/pstack/` source, adapter, provenance and supporting files. Its `.agents/skills/pstack-*` and `.claude/skills/pstack-*` aliases are **tracked relative directory symlinks to files inside this repository**. The combined guide and startup pointers are tracked too. A clone on macOS or Linux retains this layout without another repository, an absolute home-directory path, a global skill installation or a bootstrap download. Git must preserve symbolic links, as it does on the two Macs. Existing worktrees need the commit containing the package; older branches do not inherit new committed files automatically.

`upstream/` preserves the MIT plugin source byte for byte, including docs, playbooks, helpers, personas and optional Benny templates. The three Benny automation skills remain outside the main discovery set. No bundled setup, helper, hooks, model configuration or automation is activated by installation.

The repo-owned [installer](../../scripts/install_portable_engineering_skills.py) verifies this checkout with `--repo . --verify`, using Python's standard library and Git. It checks pinned pstack hashes, local skill targets, startup guidance and repository closure. Supplying `--source` is an explicit maintenance/update action; normal skill use and verification use the files already in this repository. It preserves existing Matt versions and unrelated skills, refuses unknown collisions, and never stages, commits, pushes or runs application builds. Agent discovery may refresh on the next turn. Discovery proves availability; it does not prove a persona or workflow ran.
