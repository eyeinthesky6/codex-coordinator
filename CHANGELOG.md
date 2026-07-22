# Changelog

Notable changes to Codex Coordinator will be recorded here.

## Unreleased

- Realigned the unreleased source around schema 2: a repository-scoped active-claim board owned directly by native Codex tasks, with no resident Coordinator, heartbeat, polling, full-turn reconciliation, transcript mirroring, automatic task creation, or mandatory pull-request workflow.
- Replaced the central `CURRENT.md`/task/inbox helper with bounded per-task JSON claims, revision checks, case-insensitive ancestor overlap detection, exact exclusive-action conflicts, a three-task normal limit, twelve-task hard limit, atomic writes under a short OS lock, and compact cold receipts.
- Reduced SessionStart to a five-second marker-only hint. Removed Python bootstrap scripts and all process, browser, Mission Control, history, archive, and private-Codex-data work from startup.
- Replaced Doctor self-repair, project scanning, findings, diagrams, and semantic review with a manual read-only package compatibility check whose only failure action is normal update or reinstall.
- Kept lifecycle changes dry-run-first. Schema 2 creates no Coordinator task, pin, heartbeat, schedule, or Mission Control action; legacy schema-1 projects can be disabled but cannot be reactivated without deliberate migration.
- Rewrote the capability contract, guidance, tests, and public docs around one-task-first execution, sparse non-executable peer notices, exact external-write consent, evidence-based stale recovery, direct-commit default, and optional PRs.
- Preserved the reasons and security lessons behind the superseded orchestration, Doctor, and Mission Control work in the boundary-board architectural review and Git history. The old Mission Control source remains inert pending a separate-package or removal decision.
- Kept the repository and all previously suspended projects disabled. The currently published `v0.3.0` remains the legacy orchestration release and is not changed by these unreleased source edits.

## 0.3.0 - 2026-07-17

- Published Mission Control as an optional, source-installed localhost companion with a dependency-free dashboard, project filters, settings, a bounded Doctor control, and a permanent community feedback link.
- Distinguished queued user messages from work that has actually started, so a newly submitted task no longer appears as `Working now` before the agent responds.
- Made workboard headlines use native Codex task names and reduced each card to one reviewer-facing next-action line.
- Kept Doctor focused on the installed Coordinator skill, helper, and hook plus deduplicated project-coordination findings; Mission Control validates itself through release tests and browser UAT.
- Added one optional, local-only field-report request after the first completed coordinated project plus a permanent Telegram community card in Mission Control; no feedback or usage data is sent automatically.

## 0.2.1 - 2026-07-17

- Fixed stale ownership blocking direct user requests: Coordinator now verifies the alleged owner's native state in the same turn and, when it is archived or unusable, uses the original request to recover or replace it without asking for a ping, magic phrase, or duplicate approval.
- Added a verified end-of-turn continuation gate: a Coordinator with non-terminal work must prove its heartbeat return path exists or record and surface the monitoring failure; Doctor now reports `UNATTENDED_RETURN_PATH` when a completed Coordinator turn leaves proven work without that heartbeat.
- Added a durable-thread cost gate: normal runs target one to three substantial work-area tasks, five remains the default ceiling, and routine commands, narrow checks, or low-risk one-or-two-file fixes stay with the current owner or a parent-owned subagent.
- Moved task registration, acceptance, ownership, and permission-to-continue handshakes out of visible task messages and into private coordination records; native messages are now reserved for real control actions and urgent boundary changes.
- Split the large operating guide into a short router plus execution, reconciliation, and messaging lanes so routine tasks load only applicable rules.
- Added a two-phase, disposable inbox hash checkpoint: scans remain pending until the active Coordinator durably reconciles and explicitly acknowledges each exact record hash.
- Reused host-native task cursors when available without mirroring Codex task history, and explicitly excluded codebase reads, authority, and mutable canonical state from Coordinator caching.
- Added a Mermaid decision/state map that separates instruction-driven coordination from executable validation checks.
- Rejected malformed, duplicate, or ambiguous current-state rows, reconciliation records, JSON contracts, and Doctor installation targets instead of treating them as healthy or empty.
- Preserved exact missing-state recovery warnings and Windows line endings during harmless state normalization.
- Labelled surfaced Coordinator heartbeat prompts as inter-agent messages requiring no user action, while keeping real user decisions as separate plain-language requests.
- Added optional, dependency-free Mermaid diagnostic maps to Doctor while keeping its JSON, exit status, hashes, syntax checks, and hook smoke run authoritative.
- Restyled the public site around the logo's navy, cyan, and violet palette; increased small-text size, weight, spacing, and contrast; and added a public-version consistency check.

## 0.2.0 - 2026-07-17

- Replaced empty worker holding turns and second assignment messages with one complete executable native creation prompt and immediate binding of the returned task identity.
- Made the Coordinator control-first by default while keeping subagents available as parent-owned helpers inside registered tasks.
- Added one temporary Coordinator heartbeat for live goals, a single result/blocker wake fallback, native pin/title/archive/fork/handoff lifecycle guidance, and automatic heartbeat removal at goal completion.
- Changed dispatch to inherit the user's configured model while explicitly using Low or Medium reasoning for generated Coordinator and worker tasks; High now needs a documented task-specific risk, and Extra High or Ultra requires managed policy or explicit user instruction.
- Added a dependency-free state helper for deterministic current-state validation, harmless taskless-value normalization, safe create-if-absent task/inbox records, and reconciliation-ledger validation.
- Added an installed capability contract and Doctor checks that fail structurally valid but behaviorally stale Coordinator installations.
- Removed worker identity/status handshakes: Coordinators now use the exact native creation result plus native task listing/reading, then record and dispatch the contract without asking workers to echo discovery facts.
- Added one durable worker task per coherent work area, same-area task reuse, and a default ceiling of five non-terminal workers to reduce user-visible task sprawl.
- Added terminal-task inventory and ownership-release checks so completed tasks stay closed, while independent review waits for one stable, read-only target.
- Added explicit direct-user task overrides for conflict-free work plus a durable project-local inbox for notices and resume requests while the Coordinator is busy.
- Made coordination document-first and pull-based: routine progress, findings, reviews, and completion stay in worker turns; cross-task messages are limited to assignments, exact control transitions, and urgent safety or ownership alerts.
- Added mandatory end-of-turn reconciliation records: workers persist every task, promise, dependency, blocker, and follow-up from their task window; the Coordinator must verify and disposition every row before closing the goal or declaring the project idle.
- Fixed cross-task delivery guidance so independent Codex task UUIDs use the app-native thread messenger rather than the collaboration subagent messenger, with an exact-ID retry and durable fallback.
- Required direct evidence of a later user decision before a Coordinator command may supersede a retained user constraint.
- Fixed filtered native task discovery misses so they trigger an unfiltered retry instead of asking users to bypass coordination; clarified when isolated maintenance needs no project-execution registration.
- Added an optional daily Doctor flow that scans all locally discovered enabled projects, records deduplicated evidence-backed inbox findings, and never wakes tasks or edits canonical ownership.
- Added an installed-implementation Doctor that atomically repairs the configured global skill and hook, validates the installed skill package and hook behavior, and leaves source-repository tests to the developer/release workflow.
- Fixed fresh unregistered projects being misreported as stale when their installation-standard Coordinator name is `UNREGISTERED`.
- Reworked the README around fit, first value, proof, authority boundaries, and one compact public activity row.
- Added a responsive GitHub Pages front door with pinned deployment actions, canonical metadata, structured data, crawler policy, sitemap, and an agent-readable `llms.txt` map.
- Added a problem-led discovery and recommendation guide plus automated public-site contract checks.

## 0.1.7 - 2026-07-16

- Added task-fit model and reasoning guidance, run-wide user overrides, selective Ultra escalation, and safe future-turn retuning rules.
- Made explicit multi-agent delegation without Ultra a primary product value, while documenting normal Codex usage and concurrency limits.
- Prevented paused or idle worker tasks from being reused for unrelated goals, and added receiver-side mismatch return routing to a fresh task.
- Prepared the plugin and repository for the initial open-source release.
- Hardened restart-state parsing, stale ownership detection, and packaged hook discovery.
- Clarified enablement, first-run creation, archive recovery, routing, and shared-checkout ownership.
- Added the project logo, public architecture guide, and clearer install, fit, and first-success documentation.
- Added the public support funnel, lightweight governance policy, and explicit code ownership.
- Updated pinned GitHub Actions after reviewing their release notes and passing the full CI matrix.
