# Claim lifecycle Stop-guard architectural review

- **Date:** 2026-07-22
- **Status:** Accepted and released in version `0.4.0`
- **Decision owner:** User
- **Scope:** False active claims after a native Codex task finishes or is later archived
- **Architecture boundary:** Preserve the schema-2 boundary board; do not restore orchestration

## Scope

ProfitPilot exposed a concrete correctness failure. The board reported an active claim for a task that had completed and was then archived. Native task inspection and the user's direct UI evidence proved that the board claim was stale.

This review answers four questions:

1. Which mechanism in the old orchestration design handled this problem?
2. Did the old design receive a reliable app-archive event?
3. What is the smallest current Codex lifecycle mechanism that catches the normal failure?
4. Which residual failures remain without a background watcher or private Codex database access?

It does not authorise a resident Coordinator, heartbeat, all-task reconciliation, private transcript or database inspection, automatic task creation, schedule changes, Mission Control, mandatory pull requests, or project re-enablement.

## Evidence Checked

- Current schema-2 source at `53fbc36` before this correction.
- Legacy orchestration source at `926a921` and tag `v0.3.0`.
- Exact legacy capability contract version 19 with 41 capability entries.
- Legacy `references/reconciliation.md`, `references/recovery.md`, SessionStart bootstrap, Doctor, and Mission Control source.
- Current capability contract version 22, claim helper, SessionStart, Doctor, package tests, operating guide, and simplification review.
- ProfitPilot's exact stale claim and native task evidence from the incident that triggered this review.
- Local Codex CLI `0.144.5`, including its compiled Stop-hook fields `session_id`, `cwd`, `stop_hook_active`, and `last_assistant_message`.
- Current official [Codex hook documentation](https://learn.chatgpt.com/docs/hooks), including plugin-bundled hooks, trust review, five-second-capable command hooks, Stop continuation prompts, and the unstable transcript format warning.
- OpenAI's public Stop-hook example and warning in [codex-plugin-cc](https://github.com/openai/codex-plugin-cc), plus current upstream reports about [blocking continuation failure](https://github.com/openai/codex/issues/20783) and [hook availability after rate limits or live changes](https://github.com/openai/codex/issues/21160).

## Tool Baseline

Current Codex supplies a turn-scoped `Stop` event. A command hook receives an exact session ID and working directory. It may return `{"decision":"block","reason":"..."}` to ask the same task for a continuation before the turn closes. Codex also identifies that follow-up with `stop_hook_active`, which is the required circuit breaker.

The hook input may contain a transcript path and assistant text, but those fields are unnecessary and unsafe for this product. The official documentation says the transcript format is not stable. Coordinator therefore treats both as forbidden inputs, not tempting shortcuts.

Codex does not expose an app-archive event. A task archived from the UI without first completing its normal turn cannot be discovered by a repository-local hook alone.

## Agent-Led Review

The old implementation was inspected as evidence, not copied forward. Its 41 capabilities fall into four groups:

| Group | Legacy capabilities | Original value | Effect when combined |
|---|---|---|---|
| Task and leadership policy | `workerCreation`, `coordinatorRole`, `repositoryLifecycle`, `taskCoverage`, `taskExclusions`, `pauseBehavior`, `idleBehavior`, `userStateReporting`, `deliverySummary`, `modelDefault`, `reasoningDefault`, `registrationDelivery`, `workerGranularity`, `microtaskExecution`, `parallelWorkerTarget`, `subagents`, `subagentDispatch`, `delegationDecision`, `taskTitlePolicy`, `historicalTaskReconciliation`, `taskLifecycle` | Bounded workers, visible mode, small-task discipline, explicit exclusions, stable titles, and terminal archiving | Turned one visibility aid into a permanent managing task that had to classify and report every lane |
| Reconciliation and monitoring | `monitoring`, `providerMonitoring`, `scheduledTaskReconciliation`, `coordinationReadCache`, `nativeTaskReads`, `continuationGuarantee`, `archivedRecovery`, `waitingClassification` | Catch lost results, distinguish idle from blocked, verify delivery and return paths, and recover archived owners | Required a heartbeat, task reads, caches, ledgers, provider checks, and repeated all-goal reconciliation |
| Diagnostics and runtime | `doctorDiagnostics`, `doctorProjectScan`, `doctorSemanticReview`, `missionControlLifecycle`, `pythonRuntimeBootstrap`, `lifecycleCleanup`, `globalUninstall`, `worktreeSelection`, `stateTool`, `operationsGuidance` | Easier setup, visibility, repair, cleanup, and deterministic project scans | Put bootstrap, repair, observer lifecycle, and private-state interpretation into the base package |
| Authority and safety | `providerMutationConsent`, `externalWriteDisclosure` | Prevent surprise external/provider writes and require exact consent | Valuable invariant, but provider-specific machinery did not belong in every coordination turn |

The old system's recovery guide explicitly recorded the decisive limitation: app-UI archive had no lifecycle hook. It recovered on a later action. The apparent lifecycle coverage came from the permanent Coordinator, its heartbeat, changed-turn reads, worker reconciliation reports, and terminal-worker archive action—not from a reliable native archive callback.

That machinery had genuine benefits:

- exact task identity and ownership transfer;
- limits on durable task fan-out;
- separation of microtasks from durable workers;
- evidence before calling an owner stale or blocked;
- explicit user authority for external writes and provider mutations;
- preserved recovery state;
- one consolidated view when many tasks existed.

The same machinery produced the reported symptoms:

- many near-duplicate task windows;
- one task repeatedly checking other tasks;
- scheduled heartbeat turns when nothing changed;
- per-turn ledgers and reconciliation records larger than the work result;
- Doctor and Mission Control becoming runtime subsystems;
- private Codex state and rollout coupling;
- PR, provider, and schedule checks applied to ordinary text work;
- delayed completion because every final answer became a management checkpoint.

The accepted simplification remains correct. The defect was tactical inside the new design: release depended only on an instruction to the model, with no bounded lifecycle backstop.

## Findings

### High — Terminal release was guidance-only

Schema 2 correctly made each task responsible for its own claim, but an agent could produce its final answer without running `release`. That left a structurally valid but semantically stale active record. The board then overstated active ownership.

### High — Restoring the old watcher would fix the symptom by restoring the slowdown

A permanent Coordinator could poll or inspect tasks and eventually clear stale ownership. It would also recreate the exact task count, token, latency, message, and state-authority problems that caused the realignment. This is rejected.

### Medium — Stop cannot safely infer completion

A turn may end because work is complete, because the task is waiting for the user, or because an external dependency remains. Automatically deleting every active claim at Stop could hand unfinished paths to another writer. Transcript parsing would be heuristic, private, unstable, and unnecessary.

### Medium — Blocking hooks need a circuit breaker

Upstream Codex reports show that Stop continuations and hook availability can fail in edge cases. A guard that retries indefinitely could wedge a task or consume model usage. The product must block at most once and fail open on every malformed or unavailable path.

### Medium — Hook trust is an explicit activation gate

Codex hashes non-managed hooks. A new or changed installed hook is skipped until the user reviews and trusts it. Installation proof is therefore not runtime proof; trust and a controlled live run must be verified separately.

### Low — Linked worktrees can point at the wrong board

The active board belongs to the primary worktree. A Stop hook running from a linked worktree must resolve Git's `commondir`; reading the linked checkout's local board would miss the exact claim.

## Recommended Fixes

### Implemented: one-shot exact-own-claim Stop guard

The packaged Stop hook now:

1. Reads a bounded JSON input.
2. Uses only `hook_event_name`, `session_id`, `cwd`, and `stop_hook_active`.
3. Finds an enabled schema-2 marker with a bounded parent walk.
4. Resolves the primary worktree without spawning a process.
5. Reads only `.codex/coordination/active/<session_id>.json`, capped at 4 KB.
6. Stays silent for disabled projects, missing claims, blocked claims, other task IDs, and continuation attempts.
7. For one exact active claim, asks the same task to release terminal work or explicitly retain unfinished ownership.
8. Fails open on every exception.

The guard has no matcher, no status message, no network access, no child process, no write, and a five-second timeout. It never lists the board or reads an archive.

### Retained protections

- Exact native UUID identity.
- Primary-worktree authority.
- One claim per task and expected revisions for mutations.
- Path and exclusive-action overlap detection.
- One-task default, three-task normal limit, twelve-task hard limit.
- Sparse non-executable peer notices.
- Immediate user stop.
- Exact external-write consent.
- Evidence before releasing another owner's stale claim.
- Compact cold receipts separated from the active board.
- Native Codex as transcript and lifecycle authority.
- Direct commits by default and optional pull requests.

### Rejected mechanisms

- Automatic release on every Stop.
- Transcript or assistant-message completion classification.
- Reading private Codex SQLite, rollout files, or task history.
- Scanning all active claims at Stop.
- Resident Coordinator, heartbeat, reconciliation ledger, or scheduled cleanup.
- Automatic native task archive or creation.
- Restoring Doctor repair or Mission Control lifecycle.

## Verification

Required source proof:

- unit tests for silent, exact-active, blocked, circuit-breaker, malformed, privacy, and linked-worktree cases;
- Doctor rejects missing, changed, extra, matched, or slow Stop registrations;
- package tests keep transcript/private-Codex strings and subprocess usage out of the core lifecycle scripts;
- full unit discovery passes;
- JSON parses, Python compiles, and `git diff --check` passes;
- disabled repositories stay silent;
- no Coordinator task, heartbeat, schedule, Mission Control process, or project marker is created or enabled.

Required installed proof:

- plugin manager selects version `0.4.0` from the configured marketplace;
- installed Doctor reports the current capability contract compatible;
- the user reviews and trusts the changed Stop hook;
- a controlled ProfitPilot exact claim produces one continuation on `stop_hook_active: false` and no continuation on `true`;
- releasing the claim removes it from the hot board and leaves one compact cold receipt;
- a task without an exact claim remains silent.

### Source performance sample

Twenty-five fresh Python processes per case on Windows produced:

| Stop path | p50 | p95 | Maximum output |
|---|---:|---:|---:|
| Disabled marker | 58.81 ms | 69.69 ms | 0 bytes |
| Enabled, no own claim | 56.12 ms | 63.90 ms | 0 bytes |
| Enabled, exact active claim | 56.14 ms | 63.17 ms | 549 bytes |

The near-equal times show fixed interpreter startup cost rather than task-count, transcript, archive, provider, or repository-history work. This is source evidence, not installed Codex-host proof.

## Follow-Up

The remaining UI-archive gap is accepted and visible. If Codex later provides a stable app-archive or session-end event carrying the exact native session ID, evaluate it as a replacement for on-demand stale recovery. Do not infer the event from private databases or transcripts.

Before public release, measure Stop latency on disabled, enabled-no-claim, and enabled-exact-claim paths. The target is a fixed local process cost with no dependency on task count, archive count, transcript size, or repository history.

If real usage shows repeated failures despite trusted hooks, record the exact host version and event evidence. The fallback is to disable only the Stop guard and return to manual exact release—not to restore orchestration.
