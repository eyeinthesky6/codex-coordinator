# Goal Coordinator auto-pinning without lifecycle control

Status: accepted and implemented in capability contract 35.

## Scope

Bring back the useful navigation behavior from the older release: when the user appoints one task to coordinate a repository goal, keep that task easy to find in Codex. Do this without restoring an always-on Coordinator, automatic task creation, idle management, background reconciliation, progress polling, or automatic pin cleanup.

The user job is simple: after handing a goal to one task and several workers, the person should be able to find the goal owner immediately without searching the project sidebar. The pin is a user-interface aid. It is not task authority, project state, memory, or proof that a goal is still active.

## Evidence Checked

- The current Codex host exposes native `set_thread_pinned` with one exact task ID and a boolean pin state.
- The v0.3 execution contract pinned the permanent accepting Coordinator after registration and kept it pinned through idle periods.
- The simplification reviews correctly identified the permanent accepting role, heartbeat, reconciliation, and idle retention as sources of delay. They removed automatic pinning together with that larger lifecycle.
- Contract 34 already has a safer activation boundary: the user explicitly appoints a goal-scoped Coordinator, native Goal mode binds the objective, and the exact task claims the exclusive `goal-coordination` action.
- Repository enablement and the schema-2 lifecycle helper currently create no native task or runtime component.

## Tool Baseline

Use the existing Codex pin control directly. No Python helper, project field, database, hook, scheduler, or second lifecycle service is needed.

| Need | Existing owner | Bounded use |
|---|---|---|
| Identify the goal owner | Native task identity plus `goal-coordination` claim | Exact current task only |
| Keep that task easy to find | Native `set_thread_pinned` | One best-effort pin after goal binding and claim success |
| Decide when the task leaves the pinned list | User | Coordinator never auto-unpins |
| End coordination authority | Native goal and schema-2 claim lifecycle | Normal terminal completion or stop, independent of pin state |

## Agent-Led Review

One agent reviewed the complete lifecycle because this is one narrow instruction-level change and no parallel review was requested. The review compared old pin behavior, current goal activation, installation, claim release, failure handling, public wording, Doctor compatibility, and regression tests.

## Findings

### 1. Removing all pinning discarded useful navigation

The old release made the control task easy to find. That remains valuable when several visible tasks share one goal, even though the permanent manager around it was removed.

### 2. Pinning at repository enablement would restore the wrong lifecycle

An enabled marker does not prove that a shared goal exists or that any task is its owner. Creating or pinning from installation, SessionStart, or the project lifecycle helper would recreate background management and ambiguous ownership.

### 3. Goal binding plus an exact claim is the safe activation point

The pin happens only after the user has explicitly appointed the current task, its native goal is bound, and its exact `goal-coordination` claim succeeds. Workers are never pinned by Coordinator.

### 4. A retained pin must not retain authority

At completion or stop, the Coordinator still completes or stops its native goal and releases its claim. The native pin remains only as user-owned navigation state. A pinned completed task is not accepting work, monitoring the repository, or blocking another Coordinator.

### 5. Automatic unpinning would override the user's workspace

The user may want the completed Coordinator visible for review, reuse, or history. Coordinator therefore never clears the pin or archives the task automatically. Only the user decides when to unpin it.

### 6. Pin failure is not a work blocker

A failed or ambiguous pin affects findability, not safety. Report it once and continue the authorised goal. Do not retry, poll, create a replacement task, write pin state, or start cleanup work.

## Recommended Fixes

1. After native goal binding and successful acquisition of the exact `goal-coordination` claim, call native `set_thread_pinned` once for that exact Coordinator task with `pinned: true`.
2. Never pin a worker or pin any task merely because a project is enabled.
3. Keep pin state out of `.codex/coordination/`; native Codex remains its authority.
4. Treat pin failure as a one-time non-blocking navigation warning.
5. At goal completion or stop, finish the native goal and release the claim normally, but leave the pin unchanged.
6. Never auto-unpin or auto-archive the task. The user owns that visible workspace choice.
7. Add no watcher, retry loop, heartbeat, reconciliation step, or new runtime file for pinning.

## Verification

- Capability and Doctor contracts must agree on contract 35 and user-controlled unpinning.
- Leadership and package tests must require pinning only after native goal binding and exact claim success.
- Tests must reject worker pinning, enablement pinning, automatic unpinning, automatic archiving, pin retry loops, and project pin state.
- Project-lifecycle tests must continue to prove that init, enable, disable, migrate, and purge create no native pin action.
- The full standard-library suite and `git diff --check` must pass.
- A live enabled-project trial must still confirm that the native host accepts the pin and that completing the goal releases authority while leaving the task pinned.

## Follow-Up

Run one real goal with an explicitly appointed Coordinator and one durable worker. Confirm that the Coordinator becomes pinned only after its goal and claim are active, receives the worker result without polling, completes and releases normally, and remains pinned until the user manually unpins it. If native pinning is unavailable, confirm that work continues with one plain warning and no replacement task or retry.
