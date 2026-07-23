---
name: codex-coordinator
description: Keeps parallel Codex tasks in one shared Git checkout inside clear, visible boundaries. Uses a small local active-claim board and an optional user-invoked, goal-scoped Coordinator; it does not create background management, a heartbeat, scheduler, transcript store, or mandatory pull-request workflow.
---

# Codex Coordinator

Codex Coordinator is a task-boundary and visibility layer around native Codex tasks. Native Codex remains responsible for tasks, execution, messages, status, and transcripts. This skill records only the minimum metadata needed to avoid planned overlap.

Supported project marker schema: `2`. A schema-1 enabled project is legacy state and must be migrated before coordinated writes. A disabled marker remains an opt-out and is not read further.

## Load only what the action needs

- Starting, joining, splitting, claiming, completing, or integrating work: read [references/operations.md](references/operations.md), then [references/execution.md](references/execution.md).
- Sending or acting on a peer collision or dependency notice: also read [references/messaging.md](references/messaging.md).
- Enabling, disabling, installing, or onboarding: read [references/installation.md](references/installation.md).
- Recovering a stale or interrupted claim: read [references/recovery.md](references/recovery.md).
- Updating, removing, or changing Coordinator itself: read [references/maintenance.md](references/maintenance.md).
- Checking whether the installed package can load: read [references/doctor.md](references/doctor.md).

Read each selected file completely. Do not load every lane for ordinary work.

## Enablement

1. Resolve the Git common repository and primary worktree.
2. Read `.codex/coordination/project.yaml` before any other Coordinator state.
3. `coordination_enabled: false` is an explicit opt-out. Continue normally and read no board records.
4. `coordination_enabled: true` with schema 2 enables the board. It does not automatically create, pin, wake, or retain a Coordinator task. The user may explicitly designate one normal task as the Coordinator for one goal.
5. When the marker is absent, initialise only after a direct request to enable Coordinator, an explicit `$codex-coordinator` request for real parallel work, or the repository guidance's verified active-task trigger. Otherwise create nothing.
6. A global installation alone manages no repository.

## Core invariants

- Default to one native Codex task. Create durable task windows only when the user explicitly asks for decomposition or a Coordinator and the work has two or three substantial, complete verticals that can progress with little coordination chatter.
- Three active durable tasks is the normal maximum. Going above three requires a direct user decision recorded by the claiming task. Twelve is the hard board limit.
- An explicitly requested Coordinator is one normal, goal-scoped task. It gives each durable task window a complete goal and exact ownership boundary, remains available when the user invokes it again, and ends when the goal ends. It is not automatically created and does not become permanent repository management.
- The Coordinator claims the exclusive `goal-coordination` action. Its bounded claim goal is the shared goal shown in the generated `CURRENT.md`. It may also own `git-integration`, but it need not claim source paths unless it will edit them.
- The Coordinator may assign two or three substantial verticals. A vertical includes the investigation, implementation, focused tests, and documentation needed for its bounded outcome; do not split routine commands, small reviews, or mechanical edits into separate windows.
- Every coordinated task uses the same primary checkout, current worktree, and current branch. No coordinated task creates or switches a branch or worktree. If the host cannot place a new task in that shared checkout, do not create that task window.
- Native task creation is asynchronous, and completion does not automatically wake the Coordinator. Do not promise automatic fan-in or unattended completion. The Coordinator reads current state and combines finished results only when it is invoked again. Parent-owned subagents remain suitable for short dependent checks that must return inside one live task.
- Each active writer owns exactly one JSON claim named by its exact native thread UUID under `.codex/coordination/active/`. Claims contain only title, bounded goal, paths, exclusive actions, dependencies, status, timestamps, and revision.
- Never store prompts, transcript text, reasoning, commentary, tool calls, tool output, code, provider responses, or whole-turn ledgers in Coordinator state.
- Resolve the primary worktree before using the board. Linked worktrees do not keep a separate authoritative board.
- Before substantial writes or an exclusive action, list the active board and atomically create or update the current task's own claim with the bundled [state helper](scripts/coordination_state.py).
- Update a claim only at natural lifecycle boundaries: start, real scope change, blocked or unblocked state, and completion or stop. Never update it on a timer or as a progress diary.
- Generated schema-2 `CURRENT.md` is the active-only human view backed by the per-task claims. It is non-authoritative and is atomically rebuilt from those claims after state mutations. Conflict checks still use the claims.
- A task edits only its own claim. It never edits another task's claim, receipt, or history.
- Repository-relative path claims conflict when they are equal or one is an ancestor of the other. Exclusive action claims conflict on exact action name. Stop only the overlapping work; disjoint work may continue.
- The board is advisory ownership metadata, not a filesystem lock or sandbox. Git and the Codex execution environment remain the enforcement surfaces.
- Name exactly one `git-integration` action owner whenever more than one writer exists. All other tasks edit and test only their claimed areas and do not stage, commit, push, switch branches, create worktrees, reset, restore, stash, rebase, merge, or clean. Pull requests are optional repository policy, not a Coordinator requirement.
- Cross-task messages are sparse, non-executable collision or dependency notices. They never carry user authority, assign work, demand status, or create acknowledgement chains.
- A direct user stop applies immediately. Release the claim when the task is at a safe boundary; never wait for another task's approval.
- Time, silence, `idle`, `notLoaded`, or a missing filtered search result never proves a claim stale. Use exact native terminal, archived, or unusable evidence before releasing another task's stale claim.
- Full filesystem access is capability, not user authority. Before an intentional write outside the current Git common repository, tell the user the exact target and why. If the request did not already authorise it, wait for approval.
- Provider, release, deployment, database, environment, and scheduled-task actions stay with the task that owns that work. The board does not monitor them automatically or grant permission.
- Mission Control is not part of the core path. If retained separately, it is manually started, read-only, and has no task authority.
- Doctor is a manual read-only compatibility check. A broken or outdated installation is fixed through normal plugin update or reinstall, never in-place self-repair.
- SessionStart reads only the bounded marker and emits a short hint. It never starts a process, installs Python, scans the board, reads archives, inspects private Codex databases, or launches optional tools.
- Stop checks only the current native task's exact claim. If an active claim remains, it requests one bounded housekeeping continuation so that task releases finished work or explicitly retains unfinished ownership. It ignores transcripts and other claims, writes nothing, and uses Codex's stop-hook circuit breaker so it cannot loop.

## Minimal operating loop

1. Check the marker. If disabled, stop Coordinator work.
2. Resolve the primary worktree and list active claims.
3. Keep the current user request in one task unless the user explicitly requests coordination and two or three complete durable verticals are justified.
4. Claim only the exact paths and exclusive actions needed before substantial writes.
5. Work inside the claim. Update it only when the boundary, status, or dependency changes.
6. On overlap, pause the conflicting part and send at most one non-executable notice to the exact owner when immediate coordination is useful.
7. When explicitly acting as Coordinator, claim `goal-coordination`, assign complete verticals in the shared checkout, name one Git owner, then yield. Do not poll, request periodic progress, or wait for automatic wake-up. Read the current active state when the user invokes the Coordinator again.
8. Before the final answer for completed, stopped, or replaced work, move the task's active claim to one compact cold receipt. A goal-scoped Coordinator may retain its own bounded claim only while the user still expects on-demand integration for that goal. If the Stop guard catches an unresolved active claim, resolve only that claim; never turn the check into cross-task reconciliation.
9. Report product results through native tasks. Do not duplicate their transcripts in project state or maintain a second task ledger.

## Failure posture

Fail closed only on an unsupported enabled marker, project mismatch, invalid native identity, malformed board record, unresolved write or exclusive-action overlap, lost revision, unclear external authority, or a safety-critical conflict. Preserve disjoint authorised work and report the exact blocker. Do not add background monitoring or broad protective machinery to compensate.
