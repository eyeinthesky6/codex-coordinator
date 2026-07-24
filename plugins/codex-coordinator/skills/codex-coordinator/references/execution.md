# Execution and claims

Read this file completely before creating durable tasks or changing an active claim.

## Start or join work

1. Require every `GOAL_ASSIGNMENT` to contain exactly one absolute local `Repository:` path. Resolve that path and the current task's Git worktree before activating the goal or using any target path. They must match. The assignment text does not move the task to another project. On an absent, malformed, unverifiable, or mismatched target, stop this assignment and place it in a verified native task attached to the target repository.
2. Resolve the primary worktree from the first `worktree` record in `git worktree list --porcelain`. The primary worktree owns the board even when product work runs in a linked worktree.
3. Read the marker there. A disabled marker means continue normally without reading board state. An enabled marker must use schema 2 and the exact current project ID.
4. Run the state helper's `list` command before substantial writes:

   ```text
   python <installed-skill>/scripts/coordination_state.py list --project-root <primary-worktree>
   ```

5. Read only the compact active records returned by that command. Legacy schema-1 `CURRENT.md`, task files, inbox records, archives, transcripts, and rollout logs are not active input.

Generated schema-2 `CURRENT.md` is a non-authoritative, active-only view backed by these claims and atomically rebuilt after state mutations. It is passive, pull-first visibility: read it only at a natural work boundary, never on a timer and never as a reason to message another task. A Coordinator may read it when invoked, but all conflict checks and mutations still use the individual claims.

## Choose task count for the goal

One task is the default. Investigation, implementation, tests, documentation, and follow-up fixes for one coherent outcome stay in that task.

Another durable task is justified only when all of these are true:

- the user explicitly asked for separate task windows, decomposition, or a Coordinator;
- its goal is a substantial, complete vertical worthy of a persisted native Codex goal;
- its path and exclusive-action boundary is exact;
- it can make progress without a stream of messages;
- parallel work is likely to save more time than the extra task costs;
- the complete assignment can be placed in the native creation prompt with a measurable outcome, constraints, and verification; and
- the host exposes native `get_goal` and `create_goal` to the recipient and can place it in the same primary checkout, current worktree, and current branch.

If a lane is not worth its own native Codex goal, it is not worth a durable task window. Do not create one for a test command, small lookup, formatting, narrow review follow-up, mechanical document edit, or low-risk one-or-two-file fix. Keep that work in the current task or use a parent-owned subagent when allowed by the host.

One task remains the default. Five active durable tasks is the normal project ceiling, including the
goal Coordinator. It is a stop before a sixth task, not a target to fill. When
`active_task_ceiling` is absent from the schema-2 marker, the state helper uses five. A decomposition
request authorises useful lanes, not task creation for routine commands or artificial activity.

The user may set an exact higher ceiling for the current goal in their request. That approval is
temporary: pass `--user-approved-over-limit` only for new claims above the project ceiling and never
create beyond the exact count the user named. If the user instead asks to change the project's normal
ceiling, use the dry-run-first lifecycle command in [installation.md](installation.md). At the ceiling,
an agent may ask once for either choice. State the exact proposed count, the complete lanes it enables,
the expected time saved, and the extra coordination cost. Create nothing more until the user answers;
silence, urgency, spare host capacity, or an approval from another goal is not permission.

Before creating a durable task, use the native task list to look for a related local task from the same repository and primary checkout. Inspect its native goal state. Reuse it when its context is useful, it has no unresolved user decision, and it either has no unfinished native goal or already has the same goal active. The user's explicit request for this Coordinator to decompose the shared goal authorises that bounded reuse; no extra user relay is required. A different unfinished native goal makes the task unavailable. `idle` or `notLoaded` alone proves nothing. Send one bounded `GOAL_ASSIGNMENT` as described in [messaging.md](messaging.md); the recipient creates its own active claim after binding the native goal.

For coordinated work, only the exact task holding the active `goal-coordination` action may reuse or create durable workers. Another requester or worker may ask that Coordinator once, but a failed or ambiguous handoff does not transfer creation authority and never permits fallback workers.

If no same-goal task can be reused, the Coordinator creates the smallest useful set of local tasks
in the current checkout within the current ceiling. A user-approved higher ceiling may be used only
for the goal or project scope the user named. Immediately before each creation,
make one unfiltered native task inventory for the exact repository and primary checkout.
Count the union of exact IDs from the active board and verified non-terminal native tasks already
assigned for the current goal, including the Coordinator and tasks created but not yet claimed. Use
that inventory to reuse matching assignments, prevent duplicate creation, and stop before opening a
task that would exceed the ceiling.

Before that inventory, derive one deterministic ID from the active goal instance and a unique lowercase lane key:

```text
python <installed-skill>/scripts/coordination_state.py assignment-id \
  --project-root <primary-worktree> \
  --coordinator-thread-id <exact-goal-coordinator-uuid> \
  --lane-key <unique-lane-slug>
```

Put the returned `Assignment-ID` in the complete creation prompt or reused-task `GOAL_ASSIGNMENT`. Every durable creation prompt uses that same communication shape and includes `Native-Goal: REQUIRED` plus one `Goal:` objective that states the outcome, constraints, and verification. Search the unfiltered native inventory for that exact ID and source Coordinator before creation. One verified non-terminal match is the existing assignment and must be reused. More than one match is a duplicate-task blocker. No match permits one sequential creation when the owner or agent has selected another useful lane and the host can create it.

Put the exact `--lane-key` value in `Lane-Key:` beside the returned ID. Do not abbreviate, rename,
or hand-write either value. The recipient's prompt guard recomputes the ID from the enabled board,
active goal-Coordinator claim, and lane key before it binds the native goal.

Create one task, then stop creation until the exact returned native task is read back. Verify its assignment ID, source relationship, repository working directory, complete native-goal assignment, and a short distinct human title. If the title is generic, duplicated, or contains the assignment body, rename that exact verified task once. A failed or ambiguous rename does not permit a replacement. Only after a successful identity and placement readback may the Coordinator create the next task. This immediate pre-mutation inventory and receipt check is not monitoring.

On receipt of a valid `GOAL_ASSIGNMENT`, call native `get_goal` before any repository action. If the native goal tools are unavailable, do not claim or start the durable assignment; report the host limitation so the work can remain in one task. If no unfinished goal exists, call `create_goal` with the exact `Goal:` field and no token budget unless the user explicitly supplied one. If that same objective is already active, continue it without creating another. If a different unfinished goal exists, do not replace it, claim work, or start the assignment; report that the task is not reusable. This native binding is what keeps a durable task working across continuation turns. The plugin board does not imitate it.

Never create a worktree merely to isolate a task. Before reusing an existing task, verify its repository working directory; a repository path written inside the prompt is not placement.

Native send and create operations are asynchronous. If one returns a timeout, transport failure, missing-handler error, or another result that does not prove whether the mutation ran, treat it as an unknown outcome. Make one immediate unfiltered native task readback and match the exact `Assignment-ID`, repository, recipient, and source task. Use one exact match as the accepted mutation. More than one is a duplicate blocker. When an ambiguous communication send has no visible match and the exact recipient UUID is known, create exactly one routing-only pending delivery record, then stop and report the native interface blocker. If task creation itself yields no exact recipient and readback finds none, stop without writing a placeholder route. Do not resend, retry creation, or open fallback tasks.

## Failed-delivery fallback

Normal delivery creates no Coordinator file. Only after a native communication send and one exact readback both fail to show a receipt for a known exact recipient, record the routing fact:

```text
python <installed-skill>/scripts/coordination_state.py pending-create \
  --project-root <primary-worktree> \
  --assignment-id <exact-assignment-id> \
  --kind <GOAL_ASSIGNMENT-or-RESULT_READY> \
  --sender-thread-id <exact-sender-uuid> \
  --recipient-thread-id <exact-recipient-uuid>
```

The helper accepts only `GOAL_ASSIGNMENT` or `RESULT_READY`, verifies that the active goal Coordinator is the sender or recipient required by that kind, and derives one stable pending-delivery ID from the routing tuple. Repeating the same command returns the existing record. The record contains only routing identity, repository, creation time, and pending state. It contains no assignment body, result, prompt, progress, transcript, reasoning, code, or tool output.

On a natural SessionStart, the hook counts only pending-delivery filenames in the exact current task UUID's directory and reads no record body. When that count is non-zero, inspect only that task:

```text
python <installed-skill>/scripts/coordination_state.py pending-list \
  --project-root <primary-worktree> \
  --recipient-thread-id <exact-current-task-uuid>
```

A routing record does not grant work authority and cannot reconstruct a missing assignment. A `GOAL_ASSIGNMENT` recipient acts only when the native assignment and required native goal are actually present; otherwise it reports the undelivered route and changes nothing. A `RESULT_READY` recipient reads and verifies the sender's native final result before acting.

Delete the pending record after the sender proves the exact native receipt:

```text
python <installed-skill>/scripts/coordination_state.py pending-resolve \
  --project-root <primary-worktree> \
  --assignment-id <exact-assignment-id> \
  --kind <GOAL_ASSIGNMENT-or-RESULT_READY> \
  --sender-thread-id <exact-sender-uuid> \
  --recipient-thread-id <exact-recipient-uuid> \
  --actor-thread-id <exact-sender-uuid> \
  --evidence native-receipt
```

The exact recipient may instead resolve it after verified recipient action by using its own UUID and `--evidence recipient-action`. Resolution deletes the active fallback record and creates no acknowledgement, archive receipt, or history entry.

This fallback never wakes a task, polls, schedules a check, or scans every recipient. Native delivery remains the automatic return path. If the host cannot deliver or resume the recipient, the pending record makes the failure durable but does not imitate a host scheduler.

## Goal-scoped Coordinator

When the user explicitly asks one task to coordinate a goal, that task may divide it across the
smallest useful set of active durable tasks within the current ceiling. The Coordinator may handle a
vertical itself or assign workers according to the goal and available host capacity. Give every task its full
goal, exact paths and actions, dependencies, verification, and completion condition in the first
assignment. The Coordinator stays responsible for that goal until the assigned results are accepted,
followed up, integrated, stopped, or returned to the user for a real decision. It is not a permanent
lead and repository enablement does not create it.

The Coordinator also uses the native goal lifecycle. On the user's explicit multi-step coordination request, call `get_goal`. Create the shared native goal when none is unfinished, continue it when it is the same objective, and never overwrite a different unfinished goal. Native Goal mode owns persistence and automatic continuation; the board only shows boundaries.

Claim the exclusive `goal-coordination` action for that Coordinator. Use its bounded claim goal as the shared goal in generated `CURRENT.md`. The Coordinator does not need a source-path claim unless it will edit that path. Only after the native goal is bound and that exact claim succeeds, call the host's native `set_thread_pinned` for the exact current Coordinator task with `pinned: true`. Do not pin workers or pin a task merely because the repository is enabled.

The pin keeps the goal owner easy for the user to find; it grants no authority and is not stored in project state. If pinning returns an error or ambiguous result, report that navigation problem once and continue the authorised goal without retrying, polling, creating a replacement, or changing task authority. Never unpin automatically; only the user decides when that task should leave their pinned list.

After assignment, call the host's native `wait_threads` once with the exact assigned task UUIDs and the latest returned cursor for each task. Wait for completion or a request for attention; ordinary commentary must not wake the Coordinator. The host accepts at most eight targets per wait, which is a host batch size rather than a Coordinator task limit. If a goal has more assigned tasks, keep stable exact-ID batches and rely on each worker's terminal return for tasks outside the current batch. Never replace this with a repository-wide inventory loop.

When one exact task completes or needs attention, verify its `Assignment-ID`, repository, source relationship, active goal Coordinator claim, and expected worker claim state. Read only the native result needed for that decision. Accept a satisfactory result, send the same task one bounded follow-up within its existing goal, reuse that task for a related next goal after its prior goal is terminal, integrate the result, ask the user for a material decision, or stop the shared goal. Do not open a replacement window merely because follow-up is needed. Continue with another event wait only while the current Coordinator turn remains active and exact assignments are unfinished. A timeout is not task progress and does not justify a status message, broad read, or retry loop.

Each worker still returns exactly once with `RESULT_READY` after releasing its claim. This is the terminal delivery fallback when the Coordinator is not currently inside the event wait. It contains no result payload. On receipt, verify the same facts and read the sender's native final result; never acknowledge the return or ask for periodic progress.

If the user explicitly requested unattended goal supervision and the event wait cannot remain open across turns, create at most one native Codex heartbeat attached to this Coordinator task, not a standalone cron task. Use a 15-minute default interval unless the user asks for another cadence. Keep the returned automation ID only in the native task context. Each heartbeat turn takes one immediate `wait_threads` snapshot of only the exact known assigned UUIDs and cursors, processes a terminal or attention event if present, and otherwise ends without commentary or project-state writes. Delete that exact heartbeat when all required assignments are terminal and integrated, the goal is stopped or awaiting a user decision, the user withdraws unattended supervision, or the exact assignments cannot be verified. Do not create a project heartbeat, scan unrelated tasks, mirror results, reconcile schedules, or retain a permanent monitor.

Short dependent checks may still use parent-owned subagents when the host supports them. This does not forbid complete durable verticals assigned by an explicit Coordinator.

## Shared checkout and Git

All coordinated task windows use the same primary checkout, current worktree, and current branch so they share the repository's untracked settings, offline runners, and local runtime context. Do not create or switch branches or worktrees. If the task-creation path would create another worktree, do not use it for coordinated work.

Establish the one shared branch before parallel writers start. After that, do not create or switch branches or worktrees. There is no durable Git owner. Each task may commit its own reviewed changes by staging only explicit files, checking the staged diff, and using an exact commit pathspec so unrelated staged work cannot enter the commit. Never use `git add .`, `git add -A`, force-push, pull, rebase, merge, reset, restore, stash, or clean while other writers are active. A normal non-force push is allowed when the user or repository workflow authorises it.

Git's index lock serializes the actual command, not an entire task. If an index lock, changed `HEAD`, foreign staged path, or remote update is found, stop that Git command, refresh the evidence, and continue after the immediate collision is gone. Do not convert it into permanent `git-integration` ownership.

Generated system maps, lockfiles, schemas, shared indexes, formatter-wide output, and full gates are integration surfaces rather than durable task property. Read-only gates may run at any time. Run a writer only after its required source changes are present; if another writer command is known to be running, let that command finish, then regenerate against the complete shared working tree and review the exact output.

## Create or update a claim

Use the exact native thread UUID. If the host does not expose an exact UUID, do not begin parallel writes; continue single-task work or report that safe board identity is unavailable.

Create revision 1 with `--expected-revision 0`:

```text
python <installed-skill>/scripts/coordination_state.py claim \
  --project-root <primary-worktree> \
  --thread-id <exact-native-thread-uuid> \
  --title <short-native-title> \
  --goal <one-bounded-goal> \
  --path <repository-relative-path> \
  --action <exclusive-action-if-any> \
  --expected-revision 0
```

For an update, pass the exact current revision. A revision mismatch means another turn changed the claim; list the board again before writing. The helper rejects exact exclusive-action overlap and rechecks after the atomic write. Path overlap is returned in `warnings` so agents can see possible shared-file work without turning a whole directory into a lock.

Two path claims overlap when they are equal or when one is an ancestor of the other. Matching is case-insensitive across common Windows and macOS filesystems. This is a warning, not a claim failure. Re-read the exact file before applying a narrow patch. If the patch context no longer matches or the same hunk changed, pause only that edit and coordinate; compatible hunks may continue.

Use `.` only when the task genuinely needs the whole repository. Prefer the narrowest useful file or directory boundary. Concrete paths only: no absolute paths, traversal, drive prefixes, or globs.

Exclusive action names are short lowercase slugs. Use the narrowest truthful action for an operation that really can have only one active executor, such as `goal-coordination`, `release-product`, `deployment-production`, or `database-migration-customer`. Do not use a broad action as a substitute for task scope. `git-integration` is a legacy advisory action and must not be used for new claims. An action never grants authority the task does not already have.

Set `--status blocked --blocked-by <thread-uuid>` only for a real dependency. A status is visibility, not a command to the other task.

Update the claim only when work starts, scope materially changes, blocked state changes, or work completes or stops. Do not write periodic progress, commentary, findings, or a heartbeat into the claim. A claim update is passive state and must not trigger an inter-agent message.

## Work and cooperative Git

- Preserve existing dirty work. Claims show planned scope but do not authorize overwriting another task's changes.
- Re-read a file before changing it, use narrow patches, and inspect the resulting diff. Stop only when the same hunk is actually incompatible.
- Before staging, inspect the current index. Stage only explicit files the task reviewed. Verify the staged names and patch, then commit only those exact paths. Leave foreign staged work untouched.
- Direct commits and pushes remain the normal path. Use a pull request only when the user or repository policy asks for one, or independent review materially benefits from an immutable remote diff.
- Pull requests are optional; the board never requires one.
- Another active path claim is visibility, not a task-level blocker. An exact exclusive-action conflict remains blocked until its active owner releases it.

## Complete and release

At a safe terminal boundary, move the claim out of the hot board before the task's final answer:

```text
python <installed-skill>/scripts/coordination_state.py release \
  --project-root <primary-worktree> \
  --thread-id <exact-native-thread-uuid> \
  --expected-revision <current-revision> \
  --status completed
```

Allowed final states are `completed`, `stopped`, `superseded`, and `stale-owner-confirmed`. The helper writes one compact cold receipt, then removes the active claim. It never archives or deletes the native Codex task.

When the released claim belongs to the exact goal Coordinator and the shared goal is complete or stopped, leave its native pin unchanged. The claim and native goal lifecycle still end normally, so the retained pin grants no continuing authority. Never archive or unpin it automatically; only the user manages that visible task after completion. Workers never change pin state.

The task reports its own result, changed files, checks, commit or diff when relevant, remaining risk, and blocker. A durable worker marks its native goal complete only after the stated outcome and verification are actually complete; it never ends a short execution turn while goal work remains. Then it releases the claim and sends exactly one `RESULT_READY` with the original `Assignment-ID` as the last tool action before the native final answer. The communication contains no result summary, logs, code, or tool output; the Coordinator reads the native result. No acknowledgement, general inbox entry, full-turn ledger, transcript mirror, or permanent Coordinator summary is required. Only a send with no visible receipt may leave the routing-only pending record described above.

The packaged Stop guard is a last-resort reminder, not a normal extra workflow. It reads only this task's exact active claim. If it requests a continuation, release finished work immediately. When work genuinely must remain owned across turns, retain or update only this task's claim and state that fact briefly. The guard does not inspect another task, infer completion from transcript text, or run more than once for the same stop attempt.
