# Inbox return boundary architectural review

> Goal-supervision follow-up (2026-07-23): [the goal-supervision review](2026-07-23_goal-supervision_architectural_review.md) adds exact native event waiting and, only for an explicitly unattended goal, one temporary native thread heartbeat. The routing-only pending notice remains payload-free and never becomes an inbox processor, wake queue, or result ledger.

## Scope

Decide whether schema 2 should restore the durable project inbox removed from v0.3, explain how tasks coordinate without it, and identify the smallest resilience feature that could return without restoring a second task system.

The review originally made no product change. Direct product use later exposed the predicted no-handler/no-visible-receipt path, and the user explicitly approved the bounded correction. Contract 33 now implements only the routing-only `pending-notices` fallback described below. It does not restore inbox payloads, acknowledgement checkpoints, reconciliation ledgers, polling, heartbeats, schedulers, transcript storage, Doctor findings, or Coordinator monitoring.

## Evidence Checked

- The v0.3 inbox contract at tag `v0.3.0`, especially `references/reconciliation.md` and the `scan-inbox` / `ack-inbox` paths in `coordination_state.py`.
- The current schema-2 task, messaging, execution, installation, and architecture contracts.
- Current package, boundary-workflow, prompt-guard, native-fault, and coordination-state tests.
- Direct product evidence that a native follow-up could return `No handler registered` without a visible recipient receipt.
- The earlier simplification and terminal-return reviews, including their retained protections and rejected hot-path loops.
- Current repository status and recent Git history. Existing unrelated working-tree changes were preserved.

## Tool Baseline

The normal transport is the native Codex task messenger. The native task remains the result and transcript authority; per-task claims remain the active boundary authority. No external library or service improves this boundary enough to justify another runtime dependency.

If native messaging cannot durably deliver an actionable notice, the existing standard-library state helper writes one small local failed-delivery record. It requires no SQLite, queue server, watcher, or background process.

## Agent-Led Review

The review traced four separate responsibilities that v0.3 combined under the word “inbox”:

1. **Delivery fallback:** an immutable local record survived a native message failure or a Coordinator that was not currently reachable.
2. **Turn reporting:** every material worker turn wrote a `TURN_RECONCILIATION` record containing its outcome and a row for every request, promise, finding, follow-up, dependency, or decision.
3. **Central reconciliation:** at the start and end of each coordinating turn, the Coordinator read every unprocessed record and changed task files plus `CURRENT.md` only after validating and disposing every row.
4. **Processing bookkeeping:** `scan-inbox` hashed every record and `ack-inbox` advanced a Coordinator-, project-, and epoch-scoped checkpoint only after durable disposition.

The first responsibility is useful resilience. The other three created the second task system and most of the decision overhead.

The current schema-2 path deliberately separates the concerns:

- per-task claims and generated `CURRENT.md` show active owners, goals, boundaries, status, and dependencies;
- native messages carry only a bounded `GOAL_ASSIGNMENT`, terminal `RESULT_READY`, or a concrete `COLLISION`, `DEPENDENCY`, or `RELEASED` notice;
- the native task final answer carries the worker result;
- deterministic assignment IDs plus one exact native readback handle an ambiguous send without blind retry;
- a true no-receipt path leaves one routing-only pending notice for the exact recipient;
- no progress report, acknowledgement, inbox scan, or periodic Coordinator turn is required.

## Findings

### 1. Do not restore the v0.3 inbox

The old inbox was append-only and intentionally durable, but normal work wrote into it on every material turn. A Coordinator could not finish while any record or ledger row lacked a disposition. That converted a delivery channel into a mandatory mirrored work ledger.

Restoring it would bring back the exact hot path removed by schema 2: worker summarisation, file creation, Coordinator scans, native-state comparison, canonical-state rewrites, hash acknowledgement, and carry-forward of unresolved rows.

### 2. Tasks currently coordinate without a plugin inbox

The active board answers “who is doing what?” Native messages answer “what concrete event needs another task to act?” Native final answers answer “what was the result?” These are already separate authorities and do not need another durable copy on normal success.

A shared inbox is therefore not required for ordinary coordination. It becomes relevant only when a required native notice cannot be confirmed as delivered.

### 3. The legitimate remaining gap is failed delivery, not acknowledgement

The corrected terminal protocol covers successful delivery and the “send committed but returned an error” case: the sender performs one exact readback and does not resend a matching receipt. It does not create a durable recovery fact when native delivery genuinely fails and no matching receipt exists.

That is the narrow case in which a local fallback may add value. Acknowledgement chains do not solve it cleanly. They double normal traffic, create acknowledgement-of-acknowledgement questions, and prove receipt rather than correct execution.

### 4. A fallback must not become an alternate command queue

Any returned mechanism must remain dormant on normal success. It must not grant authority, carry work results, replace native task state, awaken tasks on a timer, or require a Coordinator to scan it on every turn.

## Implemented Decision

Keep the native-message path and add a **pending-notice fallback**, not a general inbox:

- write only after one native send and one exact readback both fail to show a receipt;
- require the exact recipient UUID; an ambiguous task creation with no returned or read-back task identity creates no placeholder route;
- allow only an actionable `GOAL_ASSIGNMENT` or terminal `RESULT_READY` initially;
- use one record per `(project, assignment ID, kind, sender, recipient)` so creation is idempotent;
- store only routing identity, notice kind, repository, creation time, and delivery state;
- never store prompts, reasoning, transcript text, tool output, progress, findings, or the worker result;
- let SessionStart count only recognized filenames for the exact current task UUID, and inspect record bodies only through an explicit exact-recipient helper call;
- after verified native delivery or verified recipient action, delete it from the active set and retain no fallback receipt;
- do not send an acknowledgement back. Consumption is proven by the exact native receipt or the recipient's resulting state transition.

This mechanism should be named for its actual purpose, such as `pending-notices` or `failed-delivery`, rather than `inbox`, to avoid implying a general inter-task mailbox.

## Verification

Automated tests cover:

1. accepted-then-error delivery with exact receipt readback and no resend;
2. true zero-receipt classification followed by exactly one pending record;
3. exact-recipient SessionStart discovery without reading a record body or another recipient;
4. duplicate handling for the same assignment ID, kind, sender, and recipient;
5. routing through the exact active goal Coordinator;
6. sender/recipient-only resolution with matching evidence;
7. proof that a visible native receipt creates no local notice file; and
8. source and contract checks excluding scheduled work, heartbeat, polling, transcript copy, result payload, ledger rows, and acknowledgement messages.

A live host trial must still verify normal assignment delivery, normal terminal return with automatic Coordinator resume, and the host's actual behavior after a no-handler error. Those host properties cannot be guaranteed by a local plugin test.

## Follow-Up

The bounded fallback is implemented. It makes failed delivery visible but deliberately does not wake an idle task. Native task delivery remains the only automatic return path; adding a scheduler or resident watcher would recreate background orchestration and still requires a separate explicit architecture decision.

Any proposal for general mailboxes, payload storage, turn reports, acknowledgement chains, central reconciliation, or background delivery remains an architecture change requiring explicit user approval and a new decision record.
