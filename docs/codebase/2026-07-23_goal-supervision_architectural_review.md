# Goal supervision without a resident Coordinator

> Goal-owner navigation correction (2026-07-23): [the auto-pinning review](2026-07-23_goal-coordinator-auto-pinning_architectural_review.md) keeps the exact goal owner easy to find with one native pin after goal binding and claim success. The pin is user-interface state only; it adds no monitoring or authority, and Coordinator never auto-unpins it.

Status: accepted and implemented in capability contract 34; pin lifecycle follow-up is contract 35.

## Scope

Restore the useful part of Coordinator supervision: after assigning complete native-goal lanes, one goal owner must notice completion or a request for attention, inspect the result, and decide whether to accept, follow up, reuse, integrate, ask the user, or finish. Do this without restoring the old resident Coordinator, all-task reconciliation, progress polling, transcript mirroring, or project heartbeat.

This decision changes instruction and capability surfaces only. It adds no daemon, database, watcher script, network dependency, project-state field, or enabled automation during installation.

## Evidence Checked

- Current Codex host tool contracts expose `wait_threads` for up to eight exact task IDs. It returns when a target completes or needs attention; commentary does not wake it, and cursors suppress already delivered final text.
- Current Codex host tool contracts expose `automation_update` heartbeats attached to the current local task and explicitly prefer that mechanism when the same task must continue later.
- Native `get_goal`, `create_goal`, and `update_goal` remain the persisted goal authority.
- Contract 33 already supplies deterministic assignment identity, one terminal `RESULT_READY`, one exact readback after ambiguous sends, and a routing-only failed-delivery record.
- The old release history shows that repository heartbeats, per-turn reconciliation, copied results, Doctor repair, and Mission Control caused repeated management turns and user-visible slowdown.

## Tool Baseline

Use the existing Codex primitives instead of custom runtime code:

| Need | Existing owner | Bounded use |
|---|---|---|
| Persist one shared objective | Native Goal mode | One goal on the Coordinator task |
| Notice worker completion or attention | `wait_threads` | Exact assigned task IDs and latest cursors only |
| Return when the Coordinator is not waiting | Native task message | One terminal `RESULT_READY`, no payload |
| Continue an explicitly unattended goal later | Native thread heartbeat | One temporary heartbeat on the exact Coordinator task |
| Show planned ownership | Schema-2 claims | Active metadata only |

No Python wrapper is added because it would duplicate native task and automation authority.

## Agent-Led Review

One agent reviewed the vertical end to end because this change is a single protocol seam and no parallel-agent work was requested. The review traced assignment, native goal binding, task creation, completion return, failed delivery, Coordinator decision, claim release, installation, privacy, Doctor compatibility, public positioning, and regression tests.

## Findings

### 1. Contract 33 returned a signal but did not own the decision loop

The worker could send `RESULT_READY`, yet the Coordinator guidance told the task to yield and wait for that message. A missing or delayed delivery could therefore leave a valid goal with nobody evaluating finished work. The user remained the monitor.

### 2. Codex already provides the correct hot-path primitive

`wait_threads` is event-driven and exact-recipient. It wakes on completion or attention, not ordinary commentary. Using it after assignment is materially smaller than building an inbox processor, watcher, or task-state database.

### 3. Terminal return remains useful as a fallback

Workers should still send one `RESULT_READY` after releasing their claims. It returns the assignment when the Coordinator is between event waits or its previous turn ended. The notice remains payload-free, at most once, and backed by the existing ambiguous-delivery rules.

### 4. Long gaps need a bounded continuation fallback

An event wait is tied to an active turn. When the user explicitly asks for unattended supervision and workers may outlive that turn, one native heartbeat attached to the same Coordinator task can return later. This is not project enablement, a permanent schedule, or an all-task monitor.

### 5. Supervision means making a decision, not merely reporting status

On completion or attention, the Coordinator must choose one goal action: accept, send one bounded follow-up, reuse the same task, integrate, ask the user, stop, or complete. Opening a replacement task for ordinary follow-up would recreate the window explosion.

## Recommended Fixes

1. Keep the Coordinator's native goal and `goal-coordination` claim active while exact assigned results or integration remain.
2. After assignment, call one event-driven `wait_threads` on the exact known worker IDs and current cursors. The host's eight-target batch is not a plugin task cap.
3. On a completion or attention event, verify assignment and repository identity, read only the native result needed for the decision, and act on the same goal.
4. Reuse the same worker for bounded follow-up when its context remains useful. Create another durable task only for a genuinely separate complete vertical under the existing reuse-first rules.
5. Treat a wait timeout as no event. Do not narrate it, broaden the scan, or turn it into repeated status checks.
6. Retain one terminal `RESULT_READY` per worker as the between-turn delivery fallback.
7. Only when the user explicitly asks for unattended supervision, allow one native thread heartbeat on the exact Coordinator task. Default to 15 minutes, inspect only known assignments, and delete it when the goal completes, stops, needs a user decision, loses verified task identity, or the user withdraws the request.
8. Store no automation state in the repository. Do not create a standalone cron task, repository heartbeat, provider reconciler, transcript copy, result ledger, acknowledgement chain, or permanent monitor.

## Verification

- Capability and Doctor contracts must agree on contract 34 and the exact supervision behavior.
- Leadership and package tests must require event-driven exact-task waiting, terminal-return fallback, bounded follow-up decisions, and cleanup of the temporary native heartbeat.
- Tests must continue to reject project-created heartbeats, broad polling, progress messages, transcript storage, private Codex reads, and runtime coupling to `wait_threads` inside Python scripts.
- The full standard-library suite and `git diff --check` must pass.
- A live host trial remains necessary to prove a real Coordinator wait, worker completion, follow-up decision, and heartbeat deletion. Source tests can prove the packaged contract, not host event delivery.

## Follow-Up

Run one enabled-project trial with two durable workers: one completes normally and one requests attention. Confirm that the Coordinator resumes from the native event, reuses the attention task for a bounded follow-up, accepts both results, completes its native goal, releases its claim, and leaves no heartbeat. If native event delivery is reliable across the whole goal, the temporary heartbeat should remain unused.
