---
name: pstack-how
description: "Pstack how. Use for \\\"how does X work\\\", code walkthroughs before changing something, and placement / ownership / layering questions (\\\"where should this live\\\", \\\"which package owns this\\\", \\\"is this the right layer\\\"). Explains subsystem architecture, runtime flow, onboarding mental models. Use why for motivation."
disable-model-invocation: true
---

# Pstack: how

This is an explicitly invoked, namespaced entry point for Lauren Tan's canonical pstack. Resolve this SKILL.md's physical directory (follow symlinks) before reading the relative references below; do not resolve them from the consuming repository's working directory.

1. Read [the local harness and combined-workflow adapter](../../AIOS-ADAPTER.md). It governs this installation's permissions, skill-name resolution, model/tool translation, and interactions with Matt Pocock and Scout. Apply it throughout this task.
2. Read [the unmodified upstream skill](../../upstream/skills/how/SKILL.md). Resolve its relative references from that upstream file's directory and follow its appropriate steps within the adapter and repository instructions.
3. A source reference to another pstack skill resolves inside `upstream/skills/`, or to its `pstack-<folder>` entry point. Bare `teach` and `tdd` already installed for Matt Pocock retain their existing identity.
4. Return the requested result and evidence with limitations. Installation or a written plan does not establish execution, verification, or permission to take unrelated actions.
