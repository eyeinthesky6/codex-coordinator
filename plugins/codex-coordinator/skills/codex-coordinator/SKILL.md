---
name: codex-coordinator
description: Keeps parallel Codex tasks in one Git repository inside clear, visible boundaries. Uses a small local active-claim board; it does not create a resident Coordinator, heartbeat, scheduler, transcript store, or mandatory pull-request workflow.
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
4. `coordination_enabled: true` with schema 2 enables the board. It does not create, pin, wake, or retain a Coordinator task.
5. When the marker is absent, initialise only after a direct request to enable Coordinator, an explicit `$codex-coordinator` request for real parallel work, or the repository guidance's verified active-task trigger. Otherwise create nothing.
6. A global installation alone manages no repository.

## Core invariants

- Default to one native Codex task. Create another durable task only when the user asks for decomposition or the work has a substantial independent goal that can safely run in parallel.
- Three active durable tasks is the normal maximum. Going above three requires a direct user decision recorded by the claiming task. Twelve is the hard board limit.
- Never create a permanent lead task. A user-facing task may temporarily split a goal and combine results, but that role ends with the goal.
- Each active writer owns exactly one JSON claim named by its exact native thread UUID under `.codex/coordination/active/`. Claims contain only title, bounded goal, paths, exclusive actions, dependencies, status, timestamps, and revision.
- Never store prompts, transcript text, reasoning, commentary, tool calls, tool output, code, provider responses, or whole-turn ledgers in Coordinator state.
- Resolve the primary worktree before using the board. Linked worktrees do not keep a separate authoritative board.
- Before substantial writes or an exclusive action, list the active board and atomically create or update the current task's own claim with the bundled [state helper](scripts/coordination_state.py).
- A task edits only its own claim. It never edits another task's claim, receipt, or history.
- Repository-relative path claims conflict when they are equal or one is an ancestor of the other. Exclusive action claims conflict on exact action name. Stop only the overlapping work; disjoint work may continue.
- The board is advisory ownership metadata, not a filesystem lock or sandbox. Git and the Codex execution environment remain the enforcement surfaces.
- Name one `git-integration` action owner whenever more than one writer exists. A single owner may commit and push directly; pull requests are optional repository policy, not a Coordinator requirement.
- Cross-task messages are sparse, non-executable collision or dependency notices. They never carry user authority, assign work, demand status, or create acknowledgement chains.
- A direct user stop applies immediately. Release the claim when the task is at a safe boundary; never wait for another task's approval.
- Time, silence, `idle`, `notLoaded`, or a missing filtered search result never proves a claim stale. Use exact native terminal, archived, or unusable evidence before releasing another task's stale claim.
- Full filesystem access is capability, not user authority. Before an intentional write outside the current Git common repository, tell the user the exact target and why. If the request did not already authorise it, wait for approval.
- Provider, release, deployment, database, environment, and scheduled-task actions stay with the task that owns that work. The board does not monitor them automatically or grant permission.
- Mission Control is not part of the core path. If retained separately, it is manually started, read-only, and has no task authority.
- Doctor is a manual read-only compatibility check. A broken or outdated installation is fixed through normal plugin update or reinstall, never in-place self-repair.
- SessionStart reads only the bounded marker and emits a short hint. It never starts a process, installs Python, scans the board, reads archives, inspects private Codex databases, or launches optional tools.

## Minimal operating loop

1. Check the marker. If disabled, stop Coordinator work.
2. Resolve the primary worktree and list active claims.
3. Keep the current user request in one task unless a durable parallel lane is justified.
4. Claim only the exact paths and exclusive actions needed before substantial writes.
5. Work inside the claim. Update it only when the boundary, status, or dependency changes.
6. On overlap, pause the conflicting part and send at most one non-executable notice to the exact owner when immediate coordination is useful.
7. On completion, stop, or confirmed replacement, move the active claim to one compact cold receipt.
8. Report the product result from the native task. Do not create a Coordinator summary task or duplicate the transcript in project state.

## Failure posture

Fail closed only on an unsupported enabled marker, project mismatch, invalid native identity, malformed board record, unresolved write or exclusive-action overlap, lost revision, unclear external authority, or a safety-critical conflict. Preserve disjoint authorised work and report the exact blocker. Do not add background monitoring or broad protective machinery to compensate.
