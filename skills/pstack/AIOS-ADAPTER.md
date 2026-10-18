# Portable pstack adapter

The filename is retained for compatibility. This adapter requires no separate source repository, course, personal operating system, or global configuration. Read it before an upstream pstack workflow. Unmodified MIT source under `upstream/` is third-party workflow material; active system/developer/user instructions and applicable consuming-repository rules take priority.

## Resolve local sources

- The 55 main upstream skills use `pstack-<upstream-folder>` names. Existing Matt Pocock skills retain their identity/version.
- Resolve an entrypoint's physical directory before following links. This adapter's sibling `upstream/` contains source, playbooks, assets, scripts, and guides. Resolve references from their original source files; do not flatten the package or borrow a live source tree from another checkout.
- Inside pstack source, `/how`, `/tdd`, `/teach`, and similar calls mean corresponding pstack source with this adapter in force. Outside that context, bare names retain the repository's existing meaning. State the framework at handoffs.
- Read relevant bodies/playbooks rather than all 55 every turn. If using the bundled `poteto-agent` persona, provide the scoped task, applicable repo rules, and actual resolved paths to this adapter and `upstream/skills/poteto-mode/SKILL.md`. A persona file does not establish native agent registration or execution.

## One owner and one quality contract

- Where adopted, repository-local `docs/agent-engineering.md` supplies combined routing. Otherwise follow existing repo workflow. Neither requires that file in another repository. Inspect actual Matt source/entrypoints before relying on names; installed versions vary.
- Use available Matt shaping/specification/ticket capabilities where useful. Small clear work can use a concise outcome and checks. Choose one execution owner: the available Matt implementation route or `pstack-poteto-mode` for an appropriate agreed bug, performance, investigation, or feature job. Carry scope/exclusions, test boundaries, acceptance/evidence, baseline, and stop/release gates across the handoff. Stop the prior dispatcher; do not nest competing loops.
- Bounded how/why, investigation, adversarial review, benchmarking, verification, and finite worker fan-out can support either owner. Return evidence without silently expanding scope or taking over priorities.
- Selected Matt feature TDD retains pre-agreed seams and meaningful red → green slices, with refactoring at review under the inspected contract. Pstack `tdd` is a situational cheap bug-regression workflow with a useful-executable-check fallback. State the contract; do not drop required integration checks or weaken assertions to satisfy another skill's preference.
- Pstack `architect` normally continues into implementation. For design-only work, explicitly select its checkpoint and stop at the agreed artifact. Learning or architecture discussion does not implicitly authorize implementation.
- Keep Matt Standards and Spec review findings separate where available. A pstack adversarial pass adds triaged risks; it does not cancel failed acceptance or authorize all suggested fixes. Follow actual setup prerequisites rather than silently invoking setup.
- Generated verification remains draft until exercised. Maintain the feature map and replayable evidence with gaps. Local, CI, deployed, and observed-user checks are distinct proof states; one feature is not universal coverage.

## Tools, models, and independence

- Use actual exposed tools/schemas. In Claude Code, consult [the official Claude mapping](upstream/docs/harness/claude-code.md), subject to local rules. Copying files does not register a native plugin/agents.
- In Codex, translate source `Task` and `AskQuestion` only to available authorized subagent/input tools. Read/search through filesystem tools. Use real isolation where required; a `readonly` label alone does not enforce access. Report unavailable capabilities rather than claiming they ran.
- Preserve useful independent roles within slots/delegation rules. Do not invent Cursor cloud agents, Bugbot, Automations, `SendToUser`, or MCP access, or claim unavailable categories were checked. A CLI may fulfill the same authorized operation, but grants no permission for a different external action.
- Inherit active model/reasoning settings unless a supported authorized choice says otherwise. Do not force upstream model slugs, overwrite global rules, purchase API usage, or start metered panels by implication. Same-model reviewers are not cross-model verification.
- Helper CLIs may bootstrap dependencies with Bun. Inspect dependencies and use the repo's sanctioned runtime/workload policy before running them. Copied helpers are not evidence of configuration or successful execution.

## Authorization and workload

- Installation makes source available; it does not activate sticky Poteto Mode, native agents, Benny automation, overnight loops, auto-merge, model setup, or global editor settings. Existing invocation flags and user/repo authorization still apply.
- Follow consuming-repo approval, commit/PR/release, privacy, and destructive-action rules. Source reset/fresh-PR/flaky-check examples do not authorize discarding another session's work or bypassing gates. Preserve unrelated work.
- Source autonomy does not authorize external messages, ticket communications, or third-party writes. Apply actual user authorization and messaging rules; a questionnaire can remain a local draft.
- Follow local machine routing. Use `heavy-run` only if available/applicable or required there; otherwise use the repo's prescribed equivalent. No executable in another checkout is required. Isolate shared browser/server state or serialize access; never bypass checks for throughput.
- Keep secrets out of committed files. `recall`, `why`, `reflect`, and `automate-me` stay within authorized relevant evidence; no unrelated history mining or implied transcript export. For consequential unresolved choices, finish a concrete comparison and obtain the appropriate decision while independent authorized work continues.

## Teaching only when requested

Do not turn ordinary coding into a course. If this repository already has a tutor/course contract and the user is learning, that contract owns mission, records, feedback, and pacing. Pstack `teach` grounds explanations through how/why and deliberately avoids quizzes; use that explanation layer without overriding existing user-requested feedback. Preserve actual progress; source preparation does not establish mastery. Without a local tutor/course, explain as requested without requiring one elsewhere or creating learning records by implication.
