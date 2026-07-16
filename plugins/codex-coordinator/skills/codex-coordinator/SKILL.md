---
name: codex-coordinator
description: Coordinates repository-scoped work across independent Codex threads with lazy project enablement, explicit opt-out, durable identity, exact routing, bounded roles, safe parallel ownership, recovery, and installation. Use for Coordinator setup or repair, substantial parallel or overlapping work, cross-thread assignments or messages, status reconciliation, archive recovery, Coordinator maintenance, or before substantial writes when another task may be active in the same repository. Do not use for small isolated tasks or simple read-only work where coordination adds no value.
---

# Codex Coordinator

Use native Codex thread tools, repository documents, worktrees, and specialist skills. Do not build another runtime, scheduler, task service, database, dashboard, or lock manager.

Supported project marker schema: `1`. Treat any other `schema_version` as incompatible unless the installed maintenance guidance contains its explicit migration path.

## Load only the applicable lane

Read every selected file completely before acting. Load no unrelated lane. All references are one level below this file.

- **Install, enable, initialise, run the first demo, onboard users, or set project model defaults:** read [references/installation.md](references/installation.md). Also read [references/maintenance.md](references/maintenance.md) when changing existing Coordinator files or project `AGENTS.md`.
- **Start, join, assign, advise, review, route messages, share a checkout, select models, manage scope, or finish project work:** read [references/operations.md](references/operations.md).
- **Startup reconciliation, resume, compact, inaccessible Coordinator, takeover, archive replacement, or interrupted transition:** read [references/recovery.md](references/recovery.md). Also read [references/operations.md](references/operations.md) before continuing active project work, and [references/installation.md](references/installation.md) only when an enabled marker exists but `CURRENT.md` is missing.
- **Repair, harden, upgrade, remove, edit packaged or legacy hooks, change Coordinator guidance or project `AGENTS.md`, or review suggestions:** read [references/maintenance.md](references/maintenance.md). Also read [references/installation.md](references/installation.md) when the work needs the marker, discovery block, or project model-config shape.

## Canonical enablement and creation authority

At the start of every turn that will perform coordinated work, read this global skill and the applicable lane from disk. Do not rely on skill text retained from an earlier turn; this is how running projects pick up behavior updates without copying files locally.

### Project enablement trigger

This is the only project-enablement trigger. Lanes apply it; they do not define alternatives.

1. Resolve the Git root and primary worktree.
2. Check `.codex/coordination/project.yaml` before reading project coordination state.
3. `coordination_enabled: true` means enabled. Reuse and reconcile it; never reinstall or reset it.
4. `coordination_enabled: false` is an explicit opt-out. Continue normally without prompting or reading project state. Only a direct user request to enable Coordinator, or an explicit `$codex-coordinator` request for real coordinated work, may set it to `true`.
5. When the marker is absent, enable without a separate prompt only when the user asks to install or enable Coordinator, explicitly invokes `$codex-coordinator` for real coordinated work, asks for parallel or cross-thread coordination, or native discovery before substantial writes proves another currently active task in the same Git common repository.
6. If none of those conditions applies, create no Coordinator files. Small, isolated, and read-only work stays uncoordinated.

### Coordinator creation authority

Enablement alone never authorises task creation. A fresh user-owned Coordinator task may be created only when no usable Coordinator is registered and one of these conditions holds: the user directly asks to create or coordinate tasks for a real goal, including an explicit `$codex-coordinator` request; the user directly asks to continue or coordinate an already recorded non-terminal goal in an enabled repository and its registered Coordinator is confirmed unusable; or a registered same-project task must replace that confirmed unusable Coordinator under the recovery lane. Installation-only, enablement-only, status-only, read-only, maintenance-only, and small isolated requests do not.

That authority permits only the native creation call and one complete creation prompt to the exact newly created thread. It does not let the invoking task register itself, edit `CURRENT.md`, create project task files, assign workers, or act as Coordinator. The creation prompt is a one-time bootstrap grant, not a normal task-ID assignment. The exact new thread may use the narrow atomic registration exception in the operations lane; no other thread may use or replay it. If an existing Coordinator might still be usable, follow recovery and create nothing.

## Core invariants

- One Git repository is one Coordinator project. The primary worktree owns canonical state; linked worktrees never synchronize or overwrite it.
- Keep `.codex/coordination/project.yaml` trackable as the repository discovery marker. Exclude the other `.codex/coordination/` contents as local operational state with the root `.gitignore`. Do not ignore the root `AGENTS.md`, `.codex/config.toml`, or all of `.codex/`.
- For a cross-thread payload, require its project ID before reading detailed task state or payload content. For a direct user task already verified inside the same Git repository, derive the expected project ID from the primary-worktree marker before reading `CURRENT.md`; do not require or invent an incoming ID. On a cross-thread missing or mismatched identity, read no foreign task and take no action.
- `project.yaml` contains stable identity and paths. `CURRENT.md` contains current epoch, Coordinator, sessions, ownership, and pending state. Task files contain detailed contracts and history.
- Documents are authoritative. Messages only deliver or acknowledge recorded state.
- Route only to the exact registered thread ID, or the exact native canonical name when no ID is exposed. Require the current epoch, `PROJECT_EXECUTION`, `accepts=true`, and the correct role.
- Validate every required routing field before delivery. Except for the narrowly defined taskless initial coordination request in the operations lane, if any field is missing, stale, mismatched, or points to an unregistered recipient, send nothing. A receiver checks the routing header before the payload and silently discards an invalid or irrelevant message without reading, forwarding, acknowledging, or acting on it.
- Register one active project `COORDINATOR`. A `COORDINATOR_MAINTAINER` is a separate `COORDINATOR_SYSTEM / accepts=false` role and never receives project work.
- After bootstrap, only the active Coordinator may originate executable project assignments, amendments, or commands. Other roles may report or forward a non-executable user request to the Coordinator but may not command peers. The only exceptions are the one-time creation prompt under the Coordinator creation authority above and a Maintainer's recorded maintenance-control transition.
- If no usable Coordinator session exists, apply the Coordinator creation authority above; the invoking task never silently appoints itself.
- Only the active Coordinator edits `CURRENT.md` and project-execution task files. Other roles report through their completed turn or a correctly routed message.
- Keep each task bounded to the shared user goal. No agent may widen scope, take another owner's files, change the goal, or grant itself authority.
- Keep one core task goal per worker thread. A turn boundary, `idle`, `notLoaded`, or `PAUSED` status controls when that thread may receive messages; it never makes the thread reusable for a different goal. When requested work would replace the recorded individual goal instead of continuing it, the Coordinator creates a fresh bounded task in a new native thread. Do not rewrite an existing contract to disguise unrelated work as an amendment.
- Allow same-checkout parallel writers when exact write scopes are disjoint. Assign shared files and Git integration to one owner. Use a worktree only when the user asks or settings require it.
- Deliver routine coordination at the recipient's turn boundary or let the Coordinator pull it from a completed turn. Interrupt only to prevent unsafe, destructive, identity-invalid, or conflicting continued work, or to enforce a new user `PAUSE`, `STOP`, or `CANCEL`.
- Default newly dispatched independent work to the current strongest Codex model with `medium` reasoning, unless the user, managed policy, host capability, or native tool control requires otherwise.
- Keep every required routing identifier exact in Coordinator state, task contracts, tool payloads, and cross-thread messages; never remove, rename, or translate them for readability. Only commentary and final replies addressed to the user omit protocol terms such as epochs, task IDs, thread IDs, scope kinds, acceptance flags, role constants, and message-type constants. In those user-facing replies, report the plain-language outcome, current work, owner only when useful, and any blocker. When another task performed a delegated side effect, identify the executor in plain language and state separately what the reporting task coordinated or verified; use first person only for actions the reporting task performed. Show raw protocol details when the user asks for diagnostics or they are necessary to explain a rejected cross-project or outdated instruction.
- Keep Coordinator behavior global. Never copy or synchronize its SOP, skill, hook, README, templates, or operating rules into projects.
- Apply behavior and hook upgrades once in the global installation; projects pick them up when agents reload. Use the marker's `schema_version` only for project-file compatibility. Never add or synchronize a separate behavior-version file inside projects.

### `CURRENT.md` compatibility contract

Keep the state compact and use the exact hook-readable field form `**<Label>:** <value>` for: `Project ID`, `Coordination epoch`, `Coordination mode`, `Shared goal`, `Last reconciliation`, `Coordinator thread ID`, `Coordinator thread name`, `Coordinator status`, and `Accepts project messages`.

Use these exact level-two section names and canonical table column order:

- `Registered sessions`: `Thread ID | Thread name | Scope kind | Role | Task ID | Status | Accepts project messages`
- `Active tasks`: `Task ID | Owner | Role | Status`
- `Pending commands`: `Task ID | Message ID | Recipient thread ID | Message type | Status`
- `Paused work`: `Task ID | Owner | Reason | Resume condition | Status`
- `Resume queue`: `Task ID | Message ID | Resume condition | Status`
- `Blocked decisions`: `Decision ID | Task ID | Decision needed | Status`

For schema `1`, keep the legacy `Recipient thread ID` header; its value is the exact thread UUID, or the exact registered canonical thread name only when native tools expose no UUID.

Keep table headers even when a table is empty; use no data row rather than changing the shape. Put detail and history in task files. Readers resolve columns by their exact header names, so harmless reordering cannot change their meaning. Treat missing, renamed, duplicated, truncated, or malformed required fields, headings, columns, or rows as invalid state, not as an empty or healthy state.

## Minimal operating loop

1. Load the applicable lane above.
2. Verify project, epoch, role, exact recipient, task boundary, checkout, and write ownership.
3. Reconcile canonical state and pending transitions before substantial writes.
4. Reuse the active Coordinator or bootstrap one fresh Coordinator task under the documented rules.
5. Write a bounded task contract and deliver it at a safe boundary. The recorded assignment reserves its scope; the receiver's validated first work or status update confirms acceptance without a standalone acknowledgement in user chat.
6. Let agents work inside their paths; pull routine updates instead of interrupting them.
7. Reconcile completion, review, integration, blockers, or user decisions in canonical state.
8. Stop when the bounded goal is complete, blocked, outside scope, unsafe, or superseded.

## Failure posture

Fail closed only on unsupported marker schema, project mismatch, stale epoch, wrong recipient, unclear authority, unresolved write overlap, missing Git integration ownership, or safety-critical conflict. A failed lookup or message never grants new authority. Preserve authorised work, report the exact blocker, and avoid broad protective machinery.
