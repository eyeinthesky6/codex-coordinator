# Changelog

Notable changes to Codex Coordinator will be recorded here.

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
