# Active-by-default Coordinator lifecycle

## Decision

Codex Coordinator is active by default after it is enabled for a specific Git repository. Global plugin installation alone does not enable or manage any repository.

An enabled repository retains one pinned, accepting Coordinator task. Every native Codex task in the same Git common repository is managed unless the user directly excludes that task. A project with no current work is idle, but its Coordinator remains registered, pinned, accepting, and observable.

This replaces the earlier opt-in-per-goal lifecycle.

## Authoritative state

The existing repository marker and canonical records remain authoritative:

- `.codex/coordination/project.yaml` decides whether the repository is enabled.
- `.codex/coordination/CURRENT.md` records the Coordinator, operating mode, active work, and user exclusions.
- Native Codex task identity and status prove which task is pinned, available, active, idle, or archived.
- Mission Control reads and presents those records. It does not become an assignment or ownership authority.

No daemon, database, network service, or second state store is added.

## Lifecycle

1. Enabling a repository creates or recovers one native Coordinator task, records its exact identity, pins it, and establishes one repository heartbeat. If the host cannot create, pin, or verify the task, enablement reports `Attention needed` and does not claim active management.
2. Each task opened in an enabled repository loads the Coordinator contract, discovers the exact registered Coordinator, and falls under its management by default.
3. The Coordinator discovers same-repository tasks through unfiltered native inventory and reconciles them through existing bounded contracts, ownership records, turn evidence, and control messages.
4. When current work finishes, the workload becomes idle. The shared goal and completed task ownership may close, but the Coordinator registration, pin, message acceptance, and repository heartbeat remain.
5. If the registered Coordinator is archived or unusable, the next eligible same-repository task follows the existing recovery path to replace and pin it. It never silently self-elects or reuses an unrelated task.
6. Disabling coordination for the repository is a separate direct user decision. It stops active management and removes the persistent heartbeat; global installation remains available for other enabled repositories.

The read-only SessionStart hook continues to validate and report state. It does not write canonical state or create native tasks. Native task creation, pinning, recovery, and messaging remain host actions performed under the Coordinator skill's documented authority.

## Modes shown to the user

| User-visible state | Canonical mode | Meaning | Allowed Coordinator behavior |
|---|---|---|---|
| Managing | `MANAGING` | Repository is enabled and the Coordinator may manage all non-excluded same-repository tasks. | Discover, contract, assign, redirect, wake, pause, stop, reconcile, and report within recorded authority. |
| Paused - report-only | `REPORT_ONLY` | The user paused active management without disabling the repository. | Observe native and canonical state, reconcile read-only evidence, and report. Do not assign, redirect, wake, stop, resume, or change task ownership. |
| Attention needed | `ATTENTION_NEEDED` | Active management cannot be safely claimed, for example because Coordinator identity, pinning, heartbeat, state, or a required user decision is unresolved. | Preserve ownership, perform safe read-only diagnosis, and report the exact issue. Do not guess authority. |

`IDLE` describes workload only. It is not an operating mode and never means the Coordinator is unregistered.

Every consolidated Coordinator response and Mission Control project summary states the current user-visible mode and lists exclusions, including `none` when there are no exclusions.

## User-only exclusions

An exclusion is a narrow exception for one exact native task. It records:

- exact thread identity and display name;
- the direct user decision that added it;
- an optional reason;
- whether the exclusion is active or removed.

Only a direct user instruction may add or remove an exclusion. A Coordinator, worker, maintainer, Doctor finding, forwarded request, or inferred task type cannot exclude a task. Exclusion removes Coordinator management actions for that task, but the Coordinator may still list it as excluded and report its native status without reading or relaying private task content.

Repository-wide pause is not an exclusion. In report-only mode, the same exclusions remain visible and all management actions are suspended.

## Boundaries

- Enabled means the repository marker is valid and `coordination_enabled: true`; installation alone is inert.
- The Coordinator manages through existing documents and native task controls. It does not own application writes, Git integration, deployment, environment, or external publication unless a bounded task contract grants that ownership.
- SessionStart and Mission Control remain read-only observers of project authority.
- Doctor may report a missing Coordinator, pin, heartbeat, invalid mode, or invalid exclusion record. It cannot repair ownership or create tasks.
- Cross-project access, destructive Git operations, release, deployment, and publication boundaries do not change.

## Acceptance criteria

- Enabling a repository produces or recovers exactly one registered, pinned, accepting Coordinator and verifies one repository heartbeat.
- A newly observed same-repository task is managed by default without requiring a separate coordinated-goal opt-in.
- Only a verified direct user instruction can add or remove a task exclusion.
- Pausing switches to `REPORT_ONLY`; native discovery and user reporting continue, while assignment, redirection, wake, stop, resume, and ownership-changing actions are forbidden.
- Every user-facing Coordinator summary and Mission Control project view shows `Managing`, `Paused - report-only`, or `Attention needed`, plus the complete exclusion list or `none`.
- Completing all current work leaves the Coordinator registered, pinned, accepting, and idle; it does not reset to `UNREGISTERED`.
- A globally installed plugin does not manage a repository whose marker is absent or explicitly disabled.
- Existing project identity, epoch, routing, scope, ownership, and safety validation remains enforced.
- Unit tests cover enablement, migration from the old unregistered idle state, default task management, user-only exclusions, report-only action blocking, idle retention, SessionStart output, Mission Control presentation, and recovery.
