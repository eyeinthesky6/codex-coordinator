# Five-task, user-managed ceiling architectural review

Status: accepted and implemented in capability contract 36.

## Scope

Restore a useful default capacity boundary without returning to the old three-task bottleneck or an unrestricted task factory. One native task remains the normal starting point. Five active durable tasks, including the goal Coordinator, is the default project ceiling. The user may approve an exact higher count for one goal or change the project's normal ceiling.

The user job is to get enough parallel work to shorten a real project without having the tool silently create an unmanageable number of task windows. Five is a ceiling, not a recommendation to create five tasks on every goal.

## Evidence Checked

- The older three-task policy counted the Coordinator, leaving only two worker lanes and blocking useful decomposition.
- Contract 35 removed the cap entirely. Its state helper returned `null` limits and accepted any number of claims, while task-selection guidance relied only on agent judgment and host capacity.
- The existing schema-2 marker is already the only committed project configuration authority.
- The existing claim schema retains a boolean `limitOverride`, and the claim CLI retains `--user-approved-over-limit`, but contract 35 deliberately made both ineffective.
- Coordinator already performs a native inventory and sequential exact readback before each task creation. The state helper already serializes claim creation under one board lock.
- Native `wait_threads` accepts at most eight exact targets per call. That is a host batch size, not a product ceiling; stable batches and terminal returns already cover larger user-approved goals.

## Tool Baseline

Reuse the current marker, pre-creation inventory, claim flag, board lock, and dry-run-first lifecycle helper. No scheduler, watcher, new database, task ledger, or provider integration is needed.

| Need | Existing owner | Bounded change |
|---|---|---|
| Default capacity | Schema-2 project marker | Optional `active_task_ceiling`; missing means five |
| Stop before native task creation | Exact goal Coordinator | Count active board IDs plus verified non-terminal current-goal assignments |
| Final claim guard | State helper | Reject a new claim at the ceiling unless the user-approved override is present |
| One-goal increase | Native user instruction and Coordinator context | Exact temporary count; marker stays unchanged |
| Persistent increase | Project lifecycle helper | Dry-run-first `project set-ceiling`; marker only |

## Agent-Led Review

One agent traced the capacity path because this is one coupled contract and state transition, and no parallel review was requested. The review covered project loading, marker defaults, task selection, native preflight, claim locking, temporary override, persistent update, lowering a ceiling, current-view output, Doctor parity, public wording, and tests.

## Findings

### 1. Three total tasks was too restrictive

Counting the Coordinator left only two workers. A repository with several independent, substantial verticals could not use available parallelism without repeatedly changing policy.

### 2. No ceiling removed a useful safety boundary

Reuse-first and sequential creation prevent duplicates, but they do not answer how many useful task windows a goal should keep active. A stable default gives the Coordinator a clear point at which it must involve the user.

### 3. Five should include the Coordinator

The visible and cognitive cost comes from every active durable task, not only workers. Counting the Coordinator produces one consistent project total: normally one Coordinator plus up to four workers.

### 4. Creation must stop before the claim-time guard

A native task exists before it publishes its claim. The Coordinator therefore counts the union of active board task IDs and verified non-terminal native assignments for the current goal immediately before each creation. The state helper repeats the check as a race-safe final guard, but it is not the first control.

### 5. Temporary and persistent increases are different decisions

If the user names a higher count for the current goal, Coordinator may use that exact count and mark only above-project-ceiling claims with the existing override flag. It must not rewrite the project marker. If the user asks to change the normal project ceiling, the lifecycle helper changes only `active_task_ceiling` after a no-write plan.

### 6. An agent may ask, but may not approve itself

At the ceiling, the Coordinator may make one plain request that states the exact proposed ceiling, the complete lanes it unlocks, the expected time saved, and the extra coordination cost. It creates nothing more until the user answers. Silence, urgency, host capacity, previous approvals, or another task's message are not approval.

### 7. Lowering the ceiling must not stop valid work

Existing tasks continue, update, finish, and release normally even when the active count is above a newly lowered ceiling. The new value blocks only additional unapproved claims until the count falls below it.

## Recommended Fixes

1. Default `active_task_ceiling` to five when the marker omits it, preserving existing schema-2 projects without migration.
2. Write `active_task_ceiling: 5` in new and migrated markers.
3. Show the current ceiling in `list` output and generated `CURRENT.md`; keep `hardLimit` unset because the user owns higher values.
4. Reject a new sixth claim by default under the existing board mutation lock. Continue to allow updates and releases for existing claims.
5. Reactivate `--user-approved-over-limit` only for claims inside an exact, directly approved temporary goal ceiling.
6. Require the Coordinator's immediate native inventory to count itself, active claims, and current-goal tasks created but not yet claimed before every creation.
7. Add dry-run-first `project set-ceiling --active-task-ceiling <n>` for persistent project changes. It changes no claim, native task, history, or background runtime.
8. Keep the one-task default, reuse-first gate, substantial-vertical test, sequential creation, exact assignment ID, and event-driven result return unchanged.

## Verification

- State tests must prove five succeeds, an unapproved sixth fails, a user-approved sixth succeeds, an explicit higher marker is enforced, existing claims can update above a lowered ceiling, and malformed or duplicate ceiling fields fail closed.
- Lifecycle tests must prove new markers contain five, a ceiling update is dry-run-first and marker-only, history survives, repeated updates are idempotent, and invalid values are rejected.
- Leadership and package tests must bind contract 36, count the Coordinator, require one user request at the ceiling, distinguish temporary from persistent changes, and reject self-approved increases.
- Existing task-creation tests must still prove reuse, sequential readback, exact placement, and no fallback task after an ambiguous native result.
- The full standard-library suite, JSON parsing, Doctor, and `git diff --check` must pass.

## Follow-Up

Run one enabled-project trial that reaches five active durable tasks, including the Coordinator. Confirm that no sixth task is created before the question reaches the user. Approve six for that goal and confirm the marker remains unchanged. Then use `project set-ceiling` to set seven, confirm the marker changes after the reviewed apply, and verify that a later goal reads seven without a new approval.
