# Codex Coordinator operating guide

Use this guide when one project benefits from multiple Codex tasks and you want each task to have a clear
job without checking every window or untangling duplicate work. Start with one task whenever it can
finish the job safely.

The technical instructions below describe release `0.4.0`. A project remains disabled until the user
reviews its migration or installation and explicitly enables it.

## Choose the smallest path

| Need | Use |
|---|---|
| One coherent result | One native Codex task; no Coordinator state |
| Short independent help inside one task | Parent-owned subagent when allowed |
| Multiple durable writers in one repository | Schema-2 active board |
| Multiple complete durable verticals under one goal | Explicitly requested, goal-scoped Coordinator |
| One combined answer with short parallel checks | One native task with parent-owned subagents |
| Check package compatibility | Manual read-only Doctor |
| Repair a broken package | Normal plugin update or reinstall |
| Observe tasks in a UI | Manually start the optional read-only Mission Control for one project |

Do not create a durable task for a command, small lookup, narrow review follow-up, simple test, or one-or-two-file mechanical fix.

An explicit Coordinator may divide a goal across the smallest useful set of up to five active durable
tasks by default, including the Coordinator. Each task gets a complete first-turn goal and exact boundary. The Coordinator waits
for exact completion or attention events, decides the next step, and receives one terminal return
from each worker as a fallback. It never scans every task, asks for progress, or copies results into
another ledger.

## Normal daily flow

### Disabled or absent marker

Continue normal Codex work. Do not read legacy schema-1 `CURRENT.md`, task, inbox, cache, or archive state. Do not create a Coordinator task or board record.

### Enabled schema-2 marker

1. Resolve the primary worktree.
2. List active claims with the bundled state helper.
3. Keep the request in the current task unless the user explicitly requests coordination and additional complete durable tasks would materially help.
4. Before substantial writes, publish this exact native task's planned paths and narrow exclusive actions using expected revision `0`.
5. Work within the stated goal. Update the claim only at natural boundaries: start, real scope change, blocked-state change, and completion or stop.
6. Treat a path overlap as a warning. Re-read shared files and pause only an actually conflicting hunk or writer command. An exact exclusive-action conflict remains blocked.
7. Before the final answer at completion or stop, release the claim to one compact cold receipt.
8. Report from the native task. Do not duplicate the turn in project state.

Five active durable tasks, including the Coordinator, is the normal project ceiling rather than a
target. Stop before a sixth. At that point, the Coordinator may ask once for a specific higher count,
the complete extra lanes it enables, the expected time saved, and the added coordination cost. A
direct user approval may raise the ceiling for that goal only, or the user may change the project's
normal ceiling with the dry-run-first lifecycle command. Silence and spare host capacity are not
approval. Lowering the ceiling does not interrupt existing work; it prevents new unapproved claims.

### Explicit Coordinator

1. The user designates one normal task as Coordinator for one bounded goal.
2. That task claims the exclusive `goal-coordination` action. Its claim goal is the shared goal; it needs no source path unless it will edit one.
3. After its native goal is bound and the exact claim succeeds, it pins its own native task once so the goal owner stays easy to find. It never pins workers. Pin failure is reported once and does not stop work.
4. Before creating anything, it reuses only a related local task whose current claim and context match the same goal. An idle task from an earlier goal is not spare capacity. Only when none exists does it create the smallest useful number of local tasks within the current ceiling.
5. It chooses one stable lowercase `Lane-Key`, derives the lane's deterministic `Assignment-ID` with the installed state helper, and searches the full same-repository task inventory for that ID. One match is reused; more than one is a duplicate blocker. With no match, it sends each task one complete vertical with paths, actions, dependencies, checks, and completion conditions. A reused task receives one `GOAL_ASSIGNMENT`; no acknowledgement or progress-message chain follows.
6. Every task stays in the same primary checkout, current worktree, and current branch. No task creates or switches a branch or worktree after parallel writing starts.
7. There is no durable Git owner. Each task may commit only its reviewed exact files while preserving foreign staged work. Shared generators and gates have no durable owner.
8. Only the exact `goal-coordination` owner creates coordinated durable workers. A requester does not create fallback workers when a handoff fails.
9. Immediately before each creation, the Coordinator performs one unfiltered native inventory to find a matching assignment ID, prevent duplicate creation, and count active same-goal tasks that may not yet have claims. The state helper repeats the ceiling check while holding the board mutation lock.
10. It creates one task at a time with the same `Assignment-ID`, then reads back the exact task and verifies its ID, repository, source relationship, complete assignment, and short distinct title before creating another.
11. After assignment, the Coordinator waits on the exact assigned native task IDs. Completion or a request for attention resumes it; ordinary commentary does not. It reads the relevant native result and chooses whether to accept, send one bounded follow-up to the same task, reuse it, integrate, ask the user, stop, or finish.
12. A worker releases its claim at a real terminal boundary, then sends exactly one `RESULT_READY` with the original assignment ID as its last tool action. This returns the assignment when the Coordinator is between event waits; it is not a progress message.
13. If the user explicitly asks for unattended supervision and the event wait cannot remain open, the Coordinator may attach one temporary 15-minute native heartbeat to its own task. Each wake checks only the known assigned task IDs. Delete it when the goal finishes, stops, needs a user decision, or cannot verify those exact assignments.
14. When the goal ends, the Coordinator completes or stops its native goal and releases its claim. It does not archive or unpin itself; the user owns that visible workspace choice.

Native task sends and creation are asynchronous. A timeout, transport error, or missing result handler does not prove failure. Perform one immediate unfiltered task readback for the exact assignment ID, repository, recipient, and source relationship. One match is the accepted operation; more than one is a duplicate blocker. If a communication send has no match and the exact recipient task is known, record one small routing-only pending delivery record and stop. If task creation returns no task identity and readback finds none, stop without inventing a placeholder. Never resend or create a fallback task. The pending delivery record contains no goal text, result, chat, or tool output; it is deleted after verified delivery or recipient action.

### Active view

Per-task JSON claims remain authoritative for warnings, exclusive-action checks, and mutations. Generated schema-2 `CURRENT.md` is a compact active-only view: shared goal from the `goal-coordination` claim, task goals, planned boundaries, status, and dependencies. It is atomically rebuilt from claims and contains no transcript or history.

## Commands

Change the normal project ceiling with a dry run first, then repeat with `--apply` after reviewing the plan:

```powershell
python plugins/codex-coordinator/scripts/codex_coordinator_project.py project set-ceiling `
  --project-root <primary-worktree> `
  --active-task-ceiling <positive-number>
```

This changes only the project marker. It preserves active claims and history. For a temporary increase,
the user instead names the exact higher count for the current goal; the marker remains unchanged.

List:

```powershell
python <installed-skill>/scripts/coordination_state.py list `
  --project-root <primary-worktree>
```

Claim:

```powershell
python <installed-skill>/scripts/coordination_state.py claim `
  --project-root <primary-worktree> `
  --thread-id <exact-native-thread-uuid> `
  --title <short-title> `
  --goal <bounded-goal> `
  --path <repo-relative-path> `
  --action <exclusive-action-if-any> `
  --expected-revision <current-or-zero>
```

Release:

```powershell
python <installed-skill>/scripts/coordination_state.py release `
  --project-root <primary-worktree> `
  --thread-id <exact-native-thread-uuid> `
  --expected-revision <current-revision> `
  --status completed
```

Allowed terminal statuses are `completed`, `stopped`, `superseded`, and `stale-owner-confirmed`.

Derive one stable lane ID before reuse or creation:

```powershell
python <installed-skill>/scripts/coordination_state.py assignment-id `
  --project-root <primary-worktree> `
  --coordinator-thread-id <exact-native-thread-uuid> `
  --lane-key <stable-short-lane-name>
```

For an ambiguous native create or send result, classify the single readback with `mutation-receipt`. `stop-unknown` means no retry:

```powershell
python <installed-skill>/scripts/coordination_state.py mutation-receipt `
  --assignment-id <ga-id> `
  --outcome ambiguous `
  --observed-assignment-id <ga-id-if-found>
```

## Claims and conflicts

- Use exact repository-relative files or directories. No absolute paths, drives, traversal, or globs.
- `.` claims the whole repository.
- Equal paths and ancestor/descendant paths warn case-insensitively; they do not reject the claim.
- Exclusive actions conflict only on the exact action slug. Use them only for truly singular operations and keep the slug narrow, such as `release-product` or `deployment-production`.
- `git-integration` is a legacy advisory action. Do not use it for new claims.
- A revision mismatch requires a fresh list. Never overwrite the newer record.
- The board is advisory metadata, not a filesystem lock or permission grant.

The helper uses a short OS file lock around mutations so concurrent writers cannot both win the same exclusive action. Each task can write only its own filename. Unknown fields and records above 4 KB are rejected.

## Git

Establish the shared branch before parallel writing. Each task may stage and commit only explicit files it reviewed. Inspect the index first, leave foreign staged work untouched, verify staged names and patch, and use exact commit paths. Do not broad-stage, switch branches, create worktrees, pull, rebase, merge, stash, reset, restore, clean, or force-push while other writers are active.

Direct commit and non-force push is the default. Pull requests are optional.

Generated system maps, lockfiles, schemas, shared indexes, formatters, and full gates have no durable owner. Read-only gates may run freely. If a writer command is already running, let that command finish, then regenerate against the complete shared working tree and review its exact output.

## Inter-agent task communication

Send a message only when an immediate real collision or dependency would otherwise surprise the exact owner. Allowed kinds are:

- `GOAL_ASSIGNMENT` — the exact active goal Coordinator gives one suitable related local task a bounded in-repository vertical;
- `RESULT_READY` — that assigned worker has released its claim and its native final result is ready;
- `COLLISION` — sender paused one actual hunk, writer command, or exclusive action;
- `DEPENDENCY` — sender cannot finish a named result until a boundary is released;
- `RELEASED` — that earlier condition is resolved.

Inter-agent task communication is plain text and non-executable. Passive status stays in the claim and is pulled only at
a natural work boundary. Before sending, prove one exact recipient must take one exact action now and
that waiting for its next board read would cause a real blocker or collision. Otherwise send nothing.
`GOAL_ASSIGNMENT` is the only assignment exception and is valid only under the user's current shared
goal, in the same repository and checkout. `RESULT_READY` carries no result payload or new authority;
it only returns the original assignment to the exact Coordinator once. Verify the same project,
assignment ID, exact sender, exact recipient, and required claim state before acting. Do not send
start, working, test-running, estimate, FYI, summary, progress, status-check, thanks, acknowledgement,
broadcast, or Coordinator-relay messages. The failed-delivery record is not a general inbox.

Each communication uses only the plain project ID, plain sender and recipient task UUIDs, one exact
boundary, and one factual effect: `Paused:`, `Blocked:`, or `Resolved:`. Do not put schema versions,
claim revisions, task status, permission language, production holds, test progress, or map state in a
message. A `RELEASED` communication reports that the earlier blocker is gone; it does not authorize work.

## Stale claims

Time, silence, `idle`, `notLoaded`, timeouts, and filtered search misses do not prove staleness.

Inspect the exact native task. Release another owner's claim only when exact evidence shows it terminal, archived, or unusable and the current direct user request covers the same unfinished work. Use `stale-owner-confirmed`; do not edit the former owner's JSON directly.

## External writes

Filesystem capability is not authority. Before writing outside the current Git common repository, tell the user the exact target and reason. If the existing request does not already authorize it, wait.

Provider, schedule, release, environment, database, and deployment actions remain owned by the task performing them. Board enablement grants none of those permissions and monitors none of them.

## Goal repository guard

Every actionable `GOAL_ASSIGNMENT` and `RESULT_READY` names one plain project ID, plain sender and recipient task UUIDs, stable lowercase `Lane-Key`, helper-derived `Assignment-ID`, and one absolute local `Repository:` path. Before that communication reaches the agent, the prompt guard verifies the enabled project and exact active goal Coordinator, recomputes the ID from the lane key, and confirms that the path and current task resolve to the same Git worktree. If a required field is absent, malformed, duplicated, invented, unverifiable, or mismatched, the turn stops with a plain explanation. Put the communication in a task attached to the named repository and generate the ID with the installed helper.

The guard is silent for normal prompts and matching terminal results. Valid assignments receive the native-goal binding instruction; valid inter-agent task communication receives only a non-executable system guard. It does not move or create tasks, read transcripts, or write files. For assignments and terminal returns only, it reads the bounded active board to prove the exact goal Coordinator and assignment identity.

## SessionStart

SessionStart reads the marker and emits a short hint for an enabled compatible project. If the exact current task has routing-only pending delivery records, it counts recognized filenames in that task's directory without reading their contents. It never scans active claims, another recipient, archives, native histories, private Codex databases, or legacy records. It launches no process, Python installer, browser, observer, task, message, heartbeat, or schedule.

## Stop guard

Stop reads only the current task's exact claim from the primary worktree. An unresolved active claim produces one housekeeping continuation: release it if the work is complete, stopped, or superseded; otherwise explicitly retain or update the claim. The `stop_hook_active` input prevents a second block.

The guard reads no transcript, assistant response, reasoning, tool output, archive, other claim, private Codex database, or native task history. It writes nothing, launches nothing, and fails open on errors. A disabled project or task without an exact claim is silent.

Codex exposes no app-archive hook. If a user abruptly archives an unfinished task, use the exact stale-owner procedure only when its claim later conflicts; do not add a watcher, heartbeat, task scan, or private database reader.

## Doctor

Run manually:

```powershell
python plugins/codex-coordinator/scripts/codex_coordinator_doctor.py --check
```

Results are `healthy` or `broken`. Broken means update or reinstall the plugin. `--apply` is a rejected legacy option and writes nothing.

Doctor does not scan projects, write findings, run a model, create a diagram, start an observer, copy files, repair, or roll back.

## Optional Mission Control

The package includes one small optional Mission Control for the launch-page viewing job. It is
manually started for one explicit enabled project, listens only on `127.0.0.1`, reads the canonical
schema-2 active board through the existing state helper, and refreshes only when the person presses
the page button. It has no task, message, model, Doctor, lifecycle, repair, schedule, or write
authority and never reads archives, transcripts, private Codex databases, or rollout files.

```powershell
python <installed-plugin>/mission_control/mission_control.py --project-root C:\Projects\your-project
```

No hook or normal Coordinator operation starts it. Press `Ctrl+C` in its terminal to stop it. The
retired v0.3 collector, lifecycle launchers, automatic refresh, project scanning, and control UI
remain historical and are not restored.

## Initialise, disable, migrate, and purge

- New-project initialisation is dry-run-first through `codex_coordinator_project.py project init`. It accepts an exact ID, name, and task prefix, and creates only the marker, empty board directories, and exact guidance/ignore blocks.
- Enablement is per repository and requires schema 2 plus direct user authority.
- Deactivation sets the marker false and removes the exact discovery block. It preserves all state and history.
- Schema-1 history remains preserved and ignored. It is never guessed into schema-2 ownership.
- Schema 1 may be disabled, then migrated with the dry-run-first lifecycle helper. Migration writes a disabled schema-2 marker, preserves the exact old marker and all legacy records, and creates no active claims.
- Migration does not inspect Codex internals. Applying it requires exact project-ID confirmation and user confirmation that the legacy heartbeat and optional observer are stopped.
- Global uninstall uses explicitly known project roots; it never scans a drive.
- Purge is separate, destructive, dry-run-first, and requires exact project-ID confirmation.

No project is re-enabled by install, update, Doctor, task discovery, SessionStart, or an optional tool.

## Validation

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The source implementation has passed the full suite, bounded performance checks, an isolated end-to-end workflow, and a read-only legacy-project migration dry run. Global installation, migration apply, real-project re-enablement, push, and release remain separate user-approved steps.

## Authority

- Current behavior: the packaged skill, capability contract, helper, lifecycle hooks, and tests.
- Architecture decision and history: [boundary-board simplification review](codebase/2026-07-21_boundary-board-simplification_architectural_review.md).
- Cooperative shared-checkout correction: [reuse-first and advisory-claim review](codebase/2026-07-23_cooperative-shared-checkout_architectural_review.md).
- Claim-lifecycle correction: [one-shot Stop guard review](codebase/2026-07-22_claim-lifecycle-stop-guard_architectural_review.md).
- Code layout: [architecture](codebase/ARCHITECTURE.md) and [structure](codebase/STRUCTURE.md).
- Destructive lifecycle boundaries: [uninstall and deactivation](codebase/UNINSTALL_AND_DEACTIVATION.md).
