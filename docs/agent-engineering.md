# Agent engineering with Matt Pocock and pstack

<!-- portable-engineering-skills:v1 -->

Use this guide as the default coding route when this repository adopts it. Choose useful steps from the task; the user need not select a skill for every step. Applicable repository instructions, user scope, and active harness rules take priority. A small clear fix needs less ceremony than a new product capability.

## Start from this checkout

The installation keeps its source here: `skills/mattpocock/`, `skills/pstack/upstream/`, the [pstack adapter](../skills/pstack/AIOS-ADAPTER.md), and local skill entrypoints. Read local files rather than borrowing a live installation from another checkout. A repository clone carries checked-in source to another machine; tools, credentials, native registration, and running services still need verification.

Read applicable `AGENTS.md`/`CLAUDE.md`, contribution/test instructions, and relevant project docs first. Inspect installed skill folders, `SKILL.md` bodies, and version notes before choosing a skill. Physical `.agents/skills/` or `.claude/skills/` entries may contain an older Matt snapshot: resolve the actual entrypoint and source. Do not silently replace registrations or mix incompatible generations within one phase. Where no native entrypoint is registered, read the local vendored source directly within the harness's invocation rules.

Matt versions vary. The inspected 38-skill snapshot includes the names below; this map does not promise every checkout has them. Older versions may use names such as `to-prd` or `to-issues`: inspect their actual contracts rather than assuming aliases. If a skill is absent, use an available equivalent or the scoped ordinary workflow, state the substitution, and never claim the missing skill ran. Installation/upgrades are separate work.

## Route the work

| Situation | Route when installed | Handoff |
|---|---|---|
| Unclear outcome or language | Matt `grill-with-docs`, `domain-modeling`; `grilling` (sometimes exposed as `grill-me`) for a bounded interview | Shared terms, constraints, decisions, unresolved questions |
| Unknown behavior or rationale | `pstack-how` for current mechanisms; `pstack-why` for rationale evidence; Matt `research` for external uncertainty | Sources, confidence, coverage gaps |
| Broad uncertainty or alternative designs | Matt `wayfinder`, `prototype`, or `codebase-design` according to local scope; bounded `pstack-architect` comparison | Whole-shape alternatives; explicitly select its checkpoint for design-only work |
| Agreed feature spanning sessions | Matt `to-spec` then `to-tickets` | Outcome, exclusions, dependencies, acceptance evidence, cold-readable work packages |
| Clear implementation | Matt `implement`; `implement-spec` for an agreed dependency graph | Tested changes under one execution owner |
| Agreed bug, performance, investigation, or feature job suited to a pstack playbook | `pstack-poteto-mode` as sole execution owner | Baseline/reproduction, scoped work, retained verification evidence |
| Acceptance | Matt `code-review`, plus warranted bounded `pstack-interrogate` risk review | Separate Standards and Spec findings; disposition of additional risks |
| Recovery or handoff | Matt `diagnosing-bugs`, `triage`, `handoff`/`claude-handoff`, `retro` as applicable | Cause/evidence, owned next step, improvement supported by actual work |

For straightforward work, establish outcome and checks in a short task contract and proceed. Ask only for missing information or consequential choices the task/repo rules cannot resolve. Do not manufacture a spec, graph, or panel for every edit. Setup, migration, guardrail, sticky-mode, and automation skills retain their invocation/authorization requirements.

## One execution owner per phase

Default to the available Matt implementation route. Choose pstack mode when its complete playbook fits the agreed job; it is a legitimate execution alternative. Make the handoff explicit in the working plan: owner, scope/exclusions, accepted test boundaries, source baseline/version, evidence, and stop/release gates. This is coordination within authorized scope, not a request for the user to operate two frameworks.

Stop the prior dispatcher before the next takes ownership. Do not run Matt `implement-spec` and pstack mode as competing coordinators for the same work. Under either owner, bounded investigation, verification, benchmarking, adversarial review, or finite `swarm` workers can return evidence without taking over priorities. Give workers owned outputs; serialize a shared browser/server or use real isolation. Parallelism requires available tools and applicable delegation permission.

## Testing, verification, and acceptance

Agree relevant behavior and test seams before implementation. When Matt feature TDD governs, use meaningful failing-before/passing-after behavior slices and keep refactoring at its review stage. `pstack-tdd` targets cheap local bug regressions and permits a useful executable check when a new test would be poor. State the selected contract and proof limitations. Neither route waives required checks or permits weakened expectations for green results.

Use existing project verification. Pstack verification creation/maintenance can improve a missing/stale harness when in scope. A generated harness is a draft until exercised; one demonstrated feature is not all-feature coverage. For performance claims, `pstack-benchmark-checklist` checks that work ran, outputs were correct, and comparisons were comparable. Source inspection, mocks, local checks, CI, deployment, and observed user behavior establish different claims.

Review against a pinned baseline and actual originating spec. Matt's review preserves Standards and Spec separately; a missing spec is a gap. If installed setup prerequisites are absent, use the existing repo review process or report the prerequisite rather than silently running setup. Pstack adversarial findings are triaged as Act on/Consider/Noted/Dismissed; they do not erase a failed acceptance axis or authorize every fix. Recheck affected behavior after accepted fixes. Follow local commit, PR, release, privacy, and destructive-action rules.

## Harness and learning boundaries

Read the [local adapter](../skills/pstack/AIOS-ADAPTER.md) before pstack source. Use actual tools and authorized model settings; report unavailable isolation/review diversity honestly. Use `heavy-run` only where available/applicable or required, or the repo's prescribed equivalent. No wrapper in another repository is a runtime prerequisite.

Coding does not automatically enter tutor mode. If the user asks to learn and this repo already has a tutor/course contract, preserve its progress and pacing. Matt `teach` and `pstack-teach` differ: pstack explains through how/why and avoids quizzes. Use it as explanation grounding without overriding an existing feedback contract. With no tutor/course, explain as requested without inventing learner records or requiring a course elsewhere.
