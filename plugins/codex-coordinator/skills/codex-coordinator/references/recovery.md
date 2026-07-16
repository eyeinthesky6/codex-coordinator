# Recovery and handoff

Read this file completely for startup reconciliation, inaccessible or archived sessions, takeover, or interrupted transitions.

## Resume from durable state

1. Resolve the primary worktree and read its marker. Never copy state from a linked worktree.
2. Verify that the marker's `schema_version` is supported by the installed global skill before reading `CURRENT.md`. On an unsupported version, do not interpret or mutate coordination state, send project messages, or begin substantial writes; report that Coordinator maintenance is required.
3. If `CURRENT.md` is missing, do not infer empty state. Follow the installation lane's **Enabled marker with missing local state** procedure. Otherwise read it and identify epoch, mode, exact Coordinator, registered sessions, tasks, and pending transitions.
4. Match the current thread ID to the session table and determine role, scope, task, and message acceptance.
5. Read only the current thread's same-project task contract.
6. Process pending `PAUSE`, `RESUME`, `STOP`, and acknowledgement state before substantial writes.
7. Use native thread tools to reconcile exact IDs and pull routine updates, blockers, and dependency requests from completed turns.
8. Do not infer death or canonical pause from age, `notLoaded`, `idle`, or an unloaded status.
9. Avoid substantial writes until authority and checkout ownership are clear.

On resume, the registered Coordinator reconciles tasks and pending commands before new work. An unloaded Coordinator remains Coordinator. SessionStart output is only a hint; canonical documents remain authoritative.

## Paused, idle, and blocked owners

Native availability and canonical task state are different. An `idle` or `notLoaded` registered task remains usable and may be woken at a safe boundary after the Coordinator records its assignment or amendment. A task recorded as `PAUSED` remains paused even when the native UI says idle; resume it only after its recorded condition clears or the current user request authorises resumption, and record `RESUME` before delivery.

When a completed worker reports that another owner blocks required scope, the Coordinator pulls that report before closing its turn and follows the blocked-owner handoff in the operations lane. Inspect the exact owner, preserve its ownership until explicit release or transfer, and pause only overlapping work. The user never relays the internal prompt.

## Coordinator election and takeover

- If no coordination is needed, keep mode `IDLE` and do not elect a new Coordinator.
- If a usable Coordinator is registered, validate the same project and epoch and use its exact address. Never self-elect merely because it is idle or unloaded.
- If no usable active Coordinator session is registered, apply the main skill's Coordinator creation authority and the operations lane's one-time bootstrap procedure. If that authority does not apply, create nothing. Retain any prior session only as history; the invoking task does not register itself or edit canonical state.
- If the prior Coordinator is confirmed archived, do not unarchive it merely to preserve its role.
- If the Coordinator only appears inaccessible, first use exact thread inspection to distinguish archived from unloaded, idle, running, or temporarily unreachable. Do not create a replacement while its state is uncertain.

The fresh Coordinator follows the operations lane's atomic registration exception: verify the marker and canonical state, advance the epoch, register itself, record any superseded thread and reason in task history, and reconcile every task before assigning work. Its native creation prompt is the one-time bootstrap grant, not a normal task-ID assignment; do not send a follow-up assignment or acknowledgement request. Never use time alone as lease expiry.

## Archived sessions

Do not ask the user to reopen threads or repair state. On the next explicit coordinated action, apply the main skill's Coordinator creation authority for an archived Coordinator, or let the registered Coordinator replace an archived worker, in the same project and local checkout. Use configured model defaults and a creation prompt containing verified project, epoch, role, task, ownership, and pending transitions. Do not create a worktree unless the user or settings require it.

- For an archived Coordinator, the invoking task creates the replacement; the replacement loads the main skill and this recovery file, verifies state, increments the epoch, registers itself, marks the old session superseded with `accepts=false`, and reconciles tasks before new assignments.
- For an archived task agent, adviser, or reviewer, the Coordinator binds the unchanged contract to the replacement, observes its validated start or internal receipt, then supersedes the old session. Do not require a visible standalone acknowledgement, widen scope, or increment the epoch.
- Do not rebind a terminal task or an already non-accepting worker session. A terminal or non-accepting former Coordinator remains history and does not block a fresh election for a new coordinated goal.

When Codex performs an archive, finish the acknowledged handoff first. App-UI archive has no lifecycle hook, so recover at the next action allowed by the main Coordinator creation authority. Navigate to the fresh user-facing Coordinator when supported; keep worker replacements in the background. If required thread tools are unavailable, preserve state and report the exact blocker. The user performs no cleanup.

Describe recovery to the user in plain language: say that coordination moved to a fresh task and existing ownership was restored. Do not expose epoch numbers, internal role constants, thread IDs, or supersession fields unless the user asks for diagnostics.

## Interrupted transitions

Treat recorded but unacknowledged transitions as pending. Treat delivered messages without matching canonical state as unauthorised. At the next safe boundary, reconcile the intended transition, delivery result, recipient state, acknowledgement, blocked dependencies, and resume queue before new work.

Reject older epochs without changing ownership; use the `STALE_EPOCH` response defined in the operations lane.
