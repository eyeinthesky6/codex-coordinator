# Codex Coordinator operating guide

Use this guide when one project needs two or three Codex tasks and you want each task to have a clear
job without checking every window or untangling duplicate work. Start with one task whenever it can
finish the job safely.

The technical instructions below describe release `0.4.0`. A project remains disabled until the user
reviews its migration or installation and explicitly enables it.

## Choose the smallest path

| Need | Use |
|---|---|
| One coherent result | One native Codex task; no Coordinator state |
| Short independent help inside one task | Parent-owned subagent when allowed |
| Two or three durable writers in one repository | Schema-2 active board |
| Two or three complete durable verticals under one goal | Explicitly requested, goal-scoped Coordinator |
| One combined answer with short parallel checks | One native task with parent-owned subagents |
| Check package compatibility | Manual read-only Doctor |
| Repair a broken package | Normal plugin update or reinstall |
| Observe tasks in a UI | No supported schema-2 observer yet |

Do not create a durable task for a command, small lookup, narrow review follow-up, simple test, or one-or-two-file mechanical fix.

An explicit Coordinator may assign two or three substantial verticals, each with a complete first-turn goal and exact boundary. It remains available when the user invokes it again for that goal. It does not monitor, poll, run a heartbeat, request periodic reports, or promise automatic fan-in; native task completion does not wake it automatically.

## Normal daily flow

### Disabled or absent marker

Continue normal Codex work. Do not read legacy schema-1 `CURRENT.md`, task, inbox, cache, or archive state. Do not create a Coordinator task or board record.

### Enabled schema-2 marker

1. Resolve the primary worktree.
2. List active claims with the bundled state helper.
3. Keep the request in the current task unless the user explicitly requests coordination and two or three complete durable verticals exist.
4. Before substantial writes, publish this exact native task's planned paths and narrow exclusive actions using expected revision `0`.
5. Work within the stated goal. Update the claim only at natural boundaries: start, real scope change, blocked-state change, and completion or stop.
6. Treat a path overlap as a warning. Re-read shared files and pause only an actually conflicting hunk or writer command. An exact exclusive-action conflict remains blocked.
7. Before the final answer at completion or stop, release the claim to one compact cold receipt.
8. Report from the native task. Do not duplicate the turn in project state.

The normal active limit is three. More requires a direct user decision and the explicit override flag. Twelve is a hard limit.

### Explicit Coordinator

1. The user designates one normal task as Coordinator for one bounded goal.
2. That task claims the exclusive `goal-coordination` action. Its claim goal is the shared goal; it needs no source path unless it will edit one.
3. Before creating anything, it reuses a suitable related local task in the same repository and checkout. Only when none exists does it create the smallest useful number of local tasks.
4. It sends each task one complete vertical with paths, actions, dependencies, checks, and completion conditions. A reused task receives one `GOAL_ASSIGNMENT`; no acknowledgement or progress-message chain follows.
5. Every task stays in the same primary checkout, current worktree, and current branch. No task creates or switches a branch or worktree after parallel writing starts.
6. There is no durable Git owner. Each task may commit only its reviewed exact files while preserving foreign staged work. Shared generators and gates have no durable owner.
7. The Coordinator yields after assignment. When the user invokes it again, it reads current active state and uses native task results only as needed. It never polls or promises automatic wake-up.

### Active view

Per-task JSON claims remain authoritative for warnings, exclusive-action checks, and mutations. Generated schema-2 `CURRENT.md` is a compact active-only view: shared goal from the `goal-coordination` claim, task goals, planned boundaries, status, and dependencies. It is atomically rebuilt from claims and contains no transcript or history.

## Commands

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

## Peer notices

Send a message only when an immediate real collision or dependency would otherwise surprise the exact owner. Allowed kinds are:

- `GOAL_ASSIGNMENT` — the exact active goal Coordinator gives one suitable related local task a bounded in-repository vertical;
- `COLLISION` — sender paused one actual hunk, writer command, or exclusive action;
- `DEPENDENCY` — sender cannot finish a named result until a boundary is released;
- `RELEASED` — that earlier condition is resolved.

Peer notices are plain text and non-executable. `GOAL_ASSIGNMENT` is the only assignment exception and is valid only under the user's current shared goal, in the same repository and checkout. It grants no deployment, release, provider, destructive, environment, or external-write authority. Verify same project, exact sender, exact recipient, and active claims before acting. No message demands progress or requires an acknowledgement.

## Stale claims

Time, silence, `idle`, `notLoaded`, timeouts, and filtered search misses do not prove staleness.

Inspect the exact native task. Release another owner's claim only when exact evidence shows it terminal, archived, or unusable and the current direct user request covers the same unfinished work. Use `stale-owner-confirmed`; do not edit the former owner's JSON directly.

## External writes

Filesystem capability is not authority. Before writing outside the current Git common repository, tell the user the exact target and reason. If the existing request does not already authorize it, wait.

Provider, schedule, release, environment, database, and deployment actions remain owned by the task performing them. Board enablement grants none of those permissions and monitors none of them.

## SessionStart

SessionStart reads only the marker and emits a short hint for an enabled compatible project. It never reads the board, archives, native histories, private Codex databases, or legacy records. It launches no process, Python installer, browser, observer, task, message, heartbeat, or schedule.

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

## Optional observers

No observer is shipped in the schema-2 base package. The retired runtime, UI, launchers, and lifecycle helper remain available only in dated decision records and historical Git revisions.

A future optional observer requires a new separate package and usage evidence. It must be manually started, read-only, and limited to the public active-board schema. It must not inspect private Codex SQLite or rollout files or have Doctor, model, task, schedule, or write authority.

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
