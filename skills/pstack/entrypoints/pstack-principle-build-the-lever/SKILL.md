---
name: pstack-principle-build-the-lever
description: "Pstack principle-build-the-lever. Apply to any non-trivial work, not just bulk work: edits, migrations, analyses, checks. Build the tool that does it or proves it (codemod, script, generator, or a skill your subagents follow) instead of working by hand. The tool is the artifact a reviewer can rerun."
disable-model-invocation: true
---

# Pstack: principle-build-the-lever

This is an explicitly invoked, namespaced entry point for Lauren Tan's canonical pstack. Resolve this SKILL.md's physical directory (follow symlinks) before reading the relative references below; do not resolve them from the consuming repository's working directory.

1. Read [the local harness and combined-workflow adapter](../../AIOS-ADAPTER.md). It governs this installation's permissions, skill-name resolution, model/tool translation, and interactions with Matt Pocock and Scout. Apply it throughout this task.
2. Read [the unmodified upstream skill](../../upstream/skills/principle-build-the-lever/SKILL.md). Resolve its relative references from that upstream file's directory and follow its appropriate steps within the adapter and repository instructions.
3. A source reference to another pstack skill resolves inside `upstream/skills/`, or to its `pstack-<folder>` entry point. Bare `teach` and `tdd` already installed for Matt Pocock retain their existing identity.
4. Return the requested result and evidence with limitations. Installation or a written plan does not establish execution, verification, or permission to take unrelated actions.
