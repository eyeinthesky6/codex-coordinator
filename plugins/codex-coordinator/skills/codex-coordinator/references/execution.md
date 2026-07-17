# Execution lane

Read this file completely when starting or joining a run, allocating native worker tasks, defining contracts and ownership, selecting reasoning, managing scope, or completing work.

## Start or join a run

1. Resolve the primary worktree from the first `worktree` record in `git worktree list --porcelain`. Read canonical Coordinator files only there. If it cannot be established safely, do not change state.
2. Read `.codex/coordination/project.yaml` first and apply the main skill's Project enablement trigger. If that trigger selects enablement, load the installation lane and finish it before coordinated work. If it does not, continue normally for local uncoordinated work and treat any incoming coordinated assignment as a mismatch.
3. For a cross-thread payload, require its project ID in the routing header before reading `CURRENT.md`, task details, or payload content. For a direct user task already verified in this Git repository, derive the expected project ID from the primary-worktree marker before reading `CURRENT.md`; it needs no incoming routing ID. One Git common repository equals one Coordinator project.
4. On a mismatch, read no foreign task and change nothing:

   ```text
   PROJECT_MISMATCH

   Assigned project:
   Current project:
   Action taken: none
   ```

   This block is for machine routing or requested diagnostics. In normal user chat, use the plain-language mismatch sentence above.

5. Read applicable `AGENTS.md`, canonical `CURRENT.md`, and only the current thread's same-project task file.
6. Do not coordinate small, isolated, or read-only work when ownership does not overlap. An enabled marker does not require every task to register for project execution. When canonical state has no active ownership or pending transition and native discovery confirms no overlap, continue directly within the user's authority. A user-authorised Coordinator Maintainer follows the maintenance lane and does not need a project-execution worker registration merely to change the Coordinator package.
7. If a registered Coordinator exists and is usable, verify its exact address, epoch, and acceptance; do not self-elect. A fresh same-repository task that is not yet registered for the requested goal writes one project-local `DIRECT_USER_NOTICE` with `state: PROCEEDING` when conflict-free work can continue, or one `COORDINATION_REQUEST` with `state: WAITING` when Coordinator action is required before safe work. It does not send a native registration request or wait for a registration acknowledgement.
8. When the main skill's Coordinator creation authority applies, use native `list_projects` and require exactly one local project whose normalized `path` equals the resolved primary-worktree path; never select by label, name, recency, or similarity. If no unique exact match exists, report that blocker and create nothing. Otherwise pass its `projectId` to `create_thread`, target the local checkout, create no worktree unless the user asks or settings require it, and bind the returned exact thread as the sole bootstrap grantee. Omit the model unless an allowed override applies and pass native `thinking: "medium"` by default; use `thinking: "low"` only for a deterministic, reversible coordination goal.
9. Put the complete one-time bootstrap grant in that native creation prompt: primary repository path, expected project ID from its marker, shared goal, requirement for the receiver to verify its own native thread identity, requirement to load this skill and applicable lanes, canonical-state verification, the atomic registration rule below, prior-state reconciliation when replacing an unusable Coordinator, and authority to create only the minimum bounded project tasks needed for the goal. Do not assign a task ID in this prompt, send a second assignment, or request a visible acknowledgement.
10. Only the exact thread created by step 8 may use the bootstrap exception. After re-verifying the primary marker and confirming the recorded Coordinator is absent or unusable as stated in its creation grant, it may perform one logical transition that registers itself as the active accepting Coordinator, advances the epoch when recovery requires it, records the shared goal, and creates the first bounded task contract before any assignment or project execution. Pin that Coordinator with `codex_app__set_thread_pinned` when the native surface supports it so the user's control task remains easy to find. This exception ends at that registration transition, grants no application ownership by itself, and cannot be replayed or used by the invoking task. On any failed precondition, change no state and report the blocker in its own turn.
11. If the registered Coordinator is merely unreachable or its archive state cannot be verified, follow the recovery lane and do not create a possible duplicate. When exact native inspection confirms it archived or unusable and the current direct user request already asks to execute or continue the recorded goal, that original request is the replacement authority; recover immediately without asking for a ping, special wording, or second confirmation. If native task creation is unavailable, preserve state and report that exact limitation; never silently self-elect.
12. Create and register ordinary worker tasks with the native-identity flow below. Never ask the new worker to discover or echo its own task ID, status, readiness, or availability. After validating the recorded assignment, the receiver may begin inside that scope; its first substantive work or status update confirms acceptance. Never require or print a standalone acknowledgement in commentary or a final reply. Send any boundary correction before editing.
13. Before selecting a worker, compare the proposed individual goal with that thread's recorded task goal and contract. Reuse the thread for continuation of the same core goal and coherent work area. A completed turn, native `idle` or `notLoaded` state, or canonical `PAUSED` state is not spare capacity for unrelated Coordinator-assigned or agent-routed work. If the proposed goal is entirely different, never wake, resume, or amend the old task for it; create a fresh bounded task and native thread only when the new-thread tests below pass, otherwise leave it undispatched. The direct-user override below is the only thread-repurposing exception.

## Thread allocation and parallelism

Optimise for a small, understandable set of durable worker threads, not the largest possible task count.

1. Map work by coherent area before dispatch. One area normally keeps one worker through investigation, implementation, focused tests, documentation, and follow-up fixes when those steps share the same core goal and ownership boundary. Amend or continue that existing task at a safe turn boundary instead of creating a thread for every checklist item or finding.
2. Apply the durable-thread gate. Create a new user-visible worker only when the work has a distinct coherent goal or ownership area, can run independently with an exact boundary, has enough parallel or continuity value to justify coordination overhead, and is substantial enough that its context is likely to remain useful after one short turn. Good durable lanes include a multi-step quality pass that will triage and repair failures, one path or feature-group investigation with related changes and validation, a broad audit with durable findings, or independent review of one stable target. Different files, phases, tools, review labels, or acceptance checks alone do not prove that a new thread is needed.
3. Routine microtasks stay inside the current owner. Do not create a project task for one lint, test, build, typecheck, formatting, or syntax command; a narrow read-only inspection or lookup; a mechanical documentation adjustment; or a low-risk local fix limited to one or two files. The owner may perform it directly or use a parent-owned subagent, then validate the result and report it in the owner's own turn. File count is a heuristic, not a safety override: a security-sensitive, destructive, architectural, or otherwise high-risk one-file change may still justify a durable lane or independent review.
4. Fold a microtask into the existing same-area worker's contract or follow-up. If no such worker exists and the entire user request is small, keep it in the current user-facing task instead of starting a coordinated project run. A Coordinator may use subagents for narrow control-plane checks, but must not use them to hide ordinary application ownership or bypass an existing owner.
5. Use one to three non-terminal project-execution workers as the normal target, excluding the Coordinator and Coordinator Maintainer. Five is the default hard ceiling. Assigned, working, blocked, and paused workers count because their context or ownership remains live. Terminal, archived, or fully released workers do not count. Four or five workers require a recorded reason why each durable lane shortens the critical path; exceed five only when the user directly sets a different run-wide limit.
6. Before every native task creation, inspect canonical state and native task status, reconcile completed work, count occupied worker slots, search for an existing same-area owner, and record why the durable-thread gate passed. If that owner is usable, continue or amend it at a safe boundary. If the ceiling is full, keep the distinct work undispatched in the Coordinator's plan until a slot is released or the user changes priorities or the limit.
7. Never evade the gate or ceiling by giving unrelated work to an existing thread, splitting one area under different labels, creating unregistered workers, promoting microtasks into durable tasks, or marking live blocked or paused work terminal. A capacity wait is not authority to contaminate another task's context.
8. When deciding whether more parallelism helps, prefer the smallest set that shortens the critical path without increasing merge contention, duplicate investigation, coordination cost, token use, or user-visible task clutter. Independent product areas may justify separate workers; several fixes in one release-hardening area usually belong to one durable worker.

### Native worker creation and status

Native Codex task tools, not worker self-report, are authoritative for task identity and runtime status.

1. After the durable-thread, new-thread, and capacity tests pass, draft the bounded task contract and record one creation-pending entry without active worker ownership. The contract contains a Coordinator-generated task ID, exact goal, scope, exclusions, ownership boundaries, acceptance criteria, stop condition, and a short reason why durable independent context is worth the coordination cost.
2. Put the complete executable assignment in the native creation prompt. Include the same project, task ID, contract, retained user constraints, required skills, and reporting boundary. This is the worker's first and only initial assignment; never create an empty holding turn or depend on a second assignment message.
3. Omit the model unless managed policy or an explicit user instruction authorises an override. Pass native `thinking: "low"` for deterministic, reversible work or `thinking: "medium"` for normal work, subject to the escalation rules below. Call the native creation tool once and use only its exact returned task ID. Never copy an identity from the prompt, title, worker reply, or surrounding conversation; a worker-supplied ID remains untrusted.
4. Immediately bind the returned native identity to the pending contract, register the worker, activate its recorded ownership, and clear the creation-pending entry. If registration cannot be completed, preserve the task as unowned and stop further delivery; never hide the failure by creating another worker.
5. Inspect that exact returned task with native listing and reading tools. Verify its repository, host, assignment delivery, and native status. A filtered lookup miss is inconclusive and follows the unfiltered retry rule in recovery. Do not ask the worker what it is doing when native tools show its status and recent turn.
6. Rename a generic title with `codex_app__set_thread_title` when the native surface supports it. Use the coherent work-area name, not a protocol ID. A rename failure does not change identity or authority.
7. The worker's validated work start is acceptance. Do not request a separate identity, readiness, availability, receipt, acknowledgement, progress, or completion message. If it entered the wrong repository or exceeded the complete creation prompt, stop only unsafe work, preserve evidence, and reconcile or replace it under the normal rules.

### Terminal-task inventory and independent review

Before waking, resuming, replacing, or creating a worker, inspect the relevant registered tasks in canonical state and their exact native status. Reconcile each task's acceptance criteria, pending transitions, blockers, paused or resume entries, and task-specific ownership; do not infer unfinished work merely because a task exists in history.

1. When a task is terminal, its accepted outcome is recorded, no pending transition or blocker remains, and all task-specific ownership is released, keep it closed. Do not wake it to restate status, availability, findings, or completion.
2. When recorded acceptance is incomplete or ownership was not actually released, reconcile the inconsistency first. Continue through a usable non-terminal same-area owner, or transfer the unfinished bounded work to a replacement under the normal creation rules. Never reactivate a terminal, non-accepting session as a shortcut.
3. Do not wake several historical specialists to re-evaluate findings already covered by current non-overlapping lanes. Pull their recorded evidence and create follow-up work only for a concrete unmet acceptance criterion.
4. Assign independent review only after the integration owner has assembled one stable commit, immutable diff, release artifact, or other exact review target. Give the reviewer read-only scope over that target and no writer or Git-integration ownership. If the target changes, record the new target and review it at the reviewer's next safe turn boundary; do not interrupt the reviewer with a moving stream of partial fixes.
5. Reuse an existing reviewer only when its recorded review goal and coherent area still match, the session remains valid and accepting, and the exact target is ready. Otherwise create one bounded replacement review task only when the normal new-thread and capacity tests pass.

## Roles and canonical state

- `COORDINATOR`: owns the shared goal, canonical state, assignments, reconciliation, and user escalation.
- `TASK_AGENT`: completes one bounded assigned outcome and requests scope changes.
- `ADVISER`: inspects and recommends without implementation ownership.
- `REVIEWER`: independently verifies without silently repairing.
- `COORDINATOR_MAINTAINER`: changes Coordinator itself only under explicit user authority; it is not a project-message recipient.

The Coordinator is control-first by default. It decomposes, dispatches, monitors, reconciles, decides integration order, and reports. Ordinary application implementation, Git integration, releases, deployments, database changes, environment changes, and provider actions belong to bounded workers. A direct user may authorise one small explicit exception when the action is conflict-free and recording a new worker would add more coordination cost than value.

Subagents remain available inside a Coordinator or worker turn when useful. They are parent-owned helpers rather than separate durable project sessions: the registered parent keeps the task contract and ownership, validates their output, and includes their work in its own final result and reconciliation. Prefer them for short standard operations such as a deterministic lint or test lane, a narrow read-only audit, or a low-risk one-or-two-file fix inside the parent's recorded boundary. Do not create a project task, canonical session, task contract, inbox registration, or user-visible Codex task for the subagent. Do not place an independent Codex task UUID in an agent-tree messenger, and do not claim that a subagent owns canonical scope separately from its parent.

Only the active project Coordinator edits `CURRENT.md` and project-execution task files, except for the exact newly created thread's one-time atomic registration transition above. Task agents, advisers, and reviewers report through their own completed turns and required append-only end-of-turn records; the Coordinator pulls and reconciles both into project documents. A Maintainer may edit only its own maintenance record and necessary maintenance transitions.

A registered task may create one unique append-only `TURN_RECONCILIATION` record in `.codex/coordination/inbox/` at the end of every material turn. The direct-user, blocked, and resume cases below may require a different inbox record before that boundary. A worker never edits or deletes any inbox record and never treats a record as canonical authority.

Keep `CURRENT.md` brief and preserve the exact fields, level-two headings, and table columns in the main skill's compatibility contract. Put predecessor and takeover detail in the applicable task history rather than changing the hook-readable shape.

Keep transition history and detailed task state in `tasks/*.md`. Control messages deliver only the few transitions that require recipient action; they never replace durable state.


## Task contracts

Include:

- project ID, shared goal, epoch, task ID, and individual goal;
- role, scope kind, message type, sender, recipient, owner thread, and message acceptance;
- retained user constraints and any recorded direct user decisions that amend them;
- resolved model and reasoning, or `inherit` / `unavailable`, plus selection source and a short task-fit rationale;
- execution mode, checkout, branch, exact write paths, and Git integration owner;
- worktree only when user-requested or settings-provided;
- included and excluded scope;
- required existing skills;
- dependencies, acceptance criteria, stop condition, and expected report.

Avoid vague goals. Name the outcome and boundary, for example: “Repair offline runner path resolution without changing production execution.”

Record skills as:

```yaml
required_skills:
  - <applicable-existing-skill>
```

## Model and reasoning selection

Inherit the user's configured model, but use cost-safe reasoning for every task generated by the Coordinator workflow. In native create and continue calls, omit the model by default and pass the native `thinking` field, or the host's equivalent reasoning field, as `low` or `medium` explicitly. This applies to bootstrap Coordinator tasks and workers, and prevents a higher host or project reasoning setting from silently multiplying coordination usage. More reasoning increases latency and usage and is not a substitute for a bounded contract.

Apply this precedence:

1. Enforce managed policy, account entitlement, destination-host capability, and the native tool's allowed model-and-reasoning combinations.
2. Apply an explicit user override for the individual task.
3. Apply an explicit run-wide user override for the current shared goal. A direction such as “use my preferred model at Extra High for all workers and use Ultra selectively” authorises that default plus selective escalation; it does not edit global or project config and expires when the shared goal closes or the user changes it.
4. Otherwise omit the model field so the native surface inherits the user's host or project model, and set reasoning to `low` or `medium` using the task-fit guidance below.
5. A task-specific `high` escalation without an explicit user override is allowed only when a wrong result has material security, architecture, recovery, financial, or irreversible impact. Record the exact reason in the task contract and mention the exceptional escalation in the Coordinator's consolidated user summary. Managed policy may require another supported level.

Select by task shape without hardcoding model slugs. Unless managed policy or the user explicitly selected a model, this selection changes reasoning only and the model continues to inherit the configured default:

- Use `low` reasoning for deterministic, reversible, tightly bounded work such as inventory, simple lookups, mechanical documentation, or focused test execution. When an allowed model override exists, a fast economical coding model is a good fit.
- Use `medium` reasoning for normal exploration, log analysis, ordinary implementation, and other work with clear acceptance criteria. When an allowed model override exists, a balanced current coding model is a good fit.
- Use `high` only for a task-specific high-risk exception under step 5 or when managed policy or an explicit user instruction requires it. Ordinary ambiguity, code review, integration, or a large repository does not by itself justify escalation.
- Use `xhigh` or the nearest supported equivalent only when managed policy or an explicit user instruction permits it for the task or run.
- Use `ultra` only when managed policy or the user explicitly permits it, the selected model and account support it, and the task materially benefits from the deepest reasoning or proactive delegation. Do not use it for routine coordination, status reconciliation, or mechanical work.

For the Coordinator thread itself, use `medium` by default and `low` only for deterministic, reversible status or maintenance work. Use `high` only for the documented high-risk exception above. Use `xhigh` or `ultra` only under managed policy or explicit user instruction. Do not make expensive reasoning a requirement for using the plugin.

For every explicit override, resolve the exact supported combination from the destination host at creation time. If an exact user choice is unavailable, do not silently substitute another model; report the limitation and use an authorised fallback only when the user or managed policy already supplied one. Never hardcode a model slug in Coordinator files.

New threads receive the resolved model override only when native policy permits it and always receive the resolved reasoning level. At the next safe continuation of a Coordinator-generated task, lower any inherited or previous reasoning above `medium` to `low` or `medium` unless managed policy or an explicit user override remains active. Record that policy-driven change and never retune an in-flight turn or create another thread merely to force a setting. Record the inherited model plus the selected reasoning level, or `unavailable` when the native tool does not expose them.

Never edit config or project guidance during ordinary coordination. Installation may set only the documented project defaults.

## Shared-checkout ownership

Allow parallel writers in the same checkout and branch when exact file or directory scopes are disjoint and recorded.

1. Each writer preserves existing dirty state, edits only owned paths, and avoids broad rewrites.
2. Give shared files such as lockfiles, schemas, generated indexes, and formatter-wide output to one owner or serialize their edits.
3. Name one Git integration owner. Other writers may inspect but must not switch branches or run broad stage, commit, reset, restore, stash, rebase, merge, clean, or checkout operations unless explicitly assigned.
4. If scopes overlap, pause only affected writes, amend ownership or serialize, and preserve completed work.
5. Create a worktree only when the user asks or settings require one. A linked worktree never owns canonical Coordinator state.

## Skills, findings, and scope

Assign existing specialist skills when useful. Keep Coordinator limited to goals, roles, ownership, routing, delivery, and stop conditions. Do not copy domain procedures into Coordinator or repair another skill without explicit user instruction.

Report application or project findings in the worker's completed turn for the Coordinator to pull, not as a cross-task message and not in the Coordinator-system suggestions folder:

```text
[PROJECT_FINDING]

Project:
Task:
Finding:
Evidence:
Impact:
Files or modules affected:
Relationship to shared goal:
Recommended action:
Can current task continue safely: YES | NO
User approval likely required: YES | NO
```

Do not silently expand a task. Use `SCOPE_CHANGE_REQUEST`, `DEPENDENT_TASK_REQUEST`, `PROJECT_FINDING`, `BLOCKED`, or `DECISION_REQUEST`.

The Coordinator may amend or create bounded dependent work without new user approval only when it remains clearly inside the shared goal, is reasonably necessary, does not materially change product behavior, avoids another owner's scope, is not substantial new work, and has no major architecture, security, trading, data, or cost implication.

Ask the user before work that is outside the shared goal, materially expands it, changes product behavior, affects multiple modules or projects, changes architecture or major dependencies, affects live trading or money, changes database schema, adds paid infrastructure, removes significant functionality, conflicts with another priority, or substantially delays the task.

For a new user instruction: continue when inside scope; record a goal, priority, dependency, or result change in the completed turn or project-local inbox for the Coordinator; and do not enter overlap until state and contracts are amended. A Coordinator amendment may refine or narrow the same individual goal, but it may not replace that goal. Entirely different Coordinator-assigned or agent-routed work requires a fresh task and native thread even when the current thread is paused or between turns. A clear direct user instruction to the current thread follows **Direct user override and durable handoff** instead. A non-Coordinator that receives a user request requiring another owner uses its completed turn or one inbox record by default; it sends one non-executable request to the active Coordinator only when immediate action is required, never sends a `USER_DIRECTIVE` command directly to that owner, and never asks the user to relay it. The Coordinator updates canonical state before responding with `CONTINUE`, `AMEND_TASK`, `PAUSE`, `STOP`, or `CREATE_DEPENDENT_TASK`.

## Task completion and release

When a task reaches an acknowledged terminal state—complete, safely cancelled or stopped, or intentionally superseded—the Coordinator reconciles the task and session separately. A pending stop or cancel does not release ownership. Replacing an archived session transfers its unchanged active task and ownership atomically; it supersedes the old session, not the task.

The worker does not send a separate completion announcement. It writes the required end-of-turn reconciliation first. The Coordinator reads that record and the final turn, verifies the acceptance evidence and actual pending work, updates task history and canonical state, releases ownership only when safe, and includes the outcome in its next consolidated user status.

1. Mark the task terminal, remove it from active tasks, and reconcile any pending commands, blockers, paused work, or resume entry tied to it.
2. Release every task-specific path, checkout, shared-file, Git-integration, runtime, deployment, database, environment, and external-action ownership.
3. Mark a task agent, adviser, or reviewer session terminal with `accepts=false`. After its result and ownership release are reconciled, archive the native worker task unless the user asked to keep completed workers visible.
4. A still-usable registered Coordinator may remain the project Coordinator between goals. Clear its completed task binding and task-specific ownership, record no active task, set both its header and registered-session status to `IDLE`, and keep `accepts=true` only for project-level coordination. Set the project to `IDLE` with no active shared goal only after all tasks, pending transitions, blockers, paused work, and resume entries are reconciled.
5. Before that Coordinator starts or assigns more executable work, record a fresh bounded task contract and new ownership. Never route new work under a terminal task.
6. If the Coordinator session is confirmed archived, terminal, or unusable, set `accepts=false` and follow the recovery lane. A native timeout, `idle`, or `notLoaded` status alone is not proof that it is unusable.

Completion never leaves task ownership attached merely because the Coordinator session remains available.

## Stop and report

Stop when the goal is achieved with evidence, a user decision is required, the task is blocked, scope expansion is needed, ownership overlaps, project identity fails, or `PAUSE` / `STOP` arrives. Do not expand into related improvements. Before reporting an ownership blocker to the user, complete the blocked-owner handoff or report the exact Coordinator routing failure; never provide manual relay instructions.

Report goal status, summary, files changed, checks, commit or diff reference when applicable, risks, unresolved items, and acceptance result. A report addressed to the Coordinator retains its task and routing identifiers. A commentary or final reply addressed to the user uses plain language and omits those identifiers unless requested. When execution was delegated, name who executed it and separately state what the reporting task coordinated, reviewed, or verified. The Coordinator decides whether to review, continue, integrate, or close.

Multiple disjoint writers are not a stop condition.
