# Terminal return and assignment receipt architectural review

> Goal-supervision follow-up (2026-07-23): [the goal-supervision review](2026-07-23_goal-supervision_architectural_review.md) makes exact native completion-or-attention waiting the primary supervision path. The one-shot `RESULT_READY` and ambiguous-delivery rules remain as the between-turn fallback.

> Failed-delivery follow-up (2026-07-23): [the inbox-return review](2026-07-23_inbox-return-boundary_architectural_review.md) preserves this at-most-once readback and adds one routing-only pending notice when the single readback has no receipt. It does not restore payloads, acknowledgements, polling, reconciliation, or a general inbox.

> Native-goal correction (2026-07-23): contract 32 keeps this assignment-ID and terminal-return protocol, but every durable lane now binds its work to native Codex Goal mode before repository action. See [the native-goal binding review](2026-07-23_native-goal-binding_architectural_review.md).

- **Date:** 2026-07-23
- **Status:** Implemented and locally verified
- **Contract:** 31

## Scope

Close three related workflow gaps without restoring the v0.3 orchestration loop:

1. an assigned worker must return control when its final result is ready, without the user waking the Coordinator;
2. an accepted native create or send whose response is lost must not be repeated blindly; and
3. the accepted-mutation/lost-response failure must be covered by deterministic integration tests.

This correction does not add polling, a heartbeat, a scheduler, progress messages, acknowledgements, an inbox, a result ledger, transcript storage, private Codex inspection, automatic fan-out, Doctor repair, or Mission Control authority.

## Evidence checked

- The schema-2 state helper, goal-Coordinator claim rules, task-creation guidance, and native message contract.
- The prompt-time repository guard and all documented actionable notice shapes.
- The live failure recorded in the boundary invariant audit: Codex accepted task sends and creates, then returned `No handler registered`.
- The current Codex task boundary: native tasks own execution and final results; the plugin cannot pass a host idempotency key or obtain a transactional creation receipt.
- Focused state, prompt-guard, package, leadership, Doctor, and fault-injection tests.

## Tool baseline

The runtime stays on the Python standard library. Native Codex remains the task, message, status, and transcript authority. Git remains the checkout authority. The schema-2 board remains bounded active ownership metadata only.

No external queue, database, workflow engine, task watcher, or retry library improves this boundary enough to justify a second authority. The smallest useful tool is a deterministic ID plus one native readback.

## Agent-led review

This is one tightly coupled protocol slice, so it was kept under one owner. The review traced assignment identity from the active goal-Coordinator claim, through reuse or native creation, into the terminal return and ambiguous-result readback. Normal success, committed-then-error, zero-receipt, and duplicate-receipt paths were reviewed as one state machine.

The logic audit shaped the outcome table below. Documentation sync then replaced only current operating claims and added supersession notes to dated history, preserving why the rejected v0.3 mechanisms once existed.

## Findings

### 1. High — native completion alone does not resume the Coordinator

The previous small contract told the Coordinator to yield, but provided no completion event. Finished workers could leave the goal paused until the user manually woke the Coordinator.

**Correction:** after reaching a real terminal boundary, the worker releases its active claim and sends exactly one `RESULT_READY` to the exact goal Coordinator. The notice contains the original assignment ID and repository but no result payload. It is the worker's last tool action before its native final answer. The Coordinator reads that native result; if the exact final turn is still finishing, it may make one event-driven wait for that task only.

This is automatic completion return, not monitoring. There are no periodic checks, progress messages, acknowledgement chain, or copied result records.

### 2. High — a native mutation can succeed before its caller receives an error

A missing handler, transport failure, or timeout does not prove that a create or send failed. Retrying can duplicate task windows or terminal messages.

**Correction:** each coordinated lane receives a deterministic `Assignment-ID`, derived from project identity, the exact active goal-Coordinator claim instance, and a stable lane key. The same ID is placed in reuse, create, and terminal-return messages. No separate ID registry is stored.

Before create, the Coordinator searches the unfiltered same-repository task inventory for that ID. After any ambiguous native result, the caller makes one exact readback. The decision table is:

| Native outcome | Exact ID matches | Decision |
|---|---:|---|
| Not attempted | 0 | Attempt once |
| Any | 1 | Use the existing task or delivered notice |
| Any | More than 1 | Stop: duplicate blocker |
| Ambiguous | 0 | Stop: unknown outcome; do not retry |
| Confirmed | 0 | Stop: missing receipt |

This gives the agent an at-most-once decision. It does not claim that the host mutation itself is transactional.

### 3. High — local tests did not cover accepted mutation plus lost response

Contract and helper tests could prove wording and pure state rules, but not the important ordering where the host commits and then reports an error.

**Correction:** a fake native host now commits a create or terminal send and then raises the observed `No handler registered` error. The integration test proves exact-ID readback finds the committed operation and the caller does not call create or send twice. A separate zero-receipt case proves ambiguous absence stops without retry.

This is deterministic host-boundary fault injection. It is not a claim that the test controls the real Codex service. A real transactional end-to-end guarantee requires supported host test hooks or a native idempotency/receipt API.

## Recommended fixes

The smallest complete correction is now implemented:

- derive one stable assignment ID per Coordinator claim instance and lane;
- require that ID and an exact local repository in `GOAL_ASSIGNMENT` and `RESULT_READY`;
- search by exact ID before creation;
- create or send once, then classify one readback after ambiguity;
- stop on duplicate, unknown, or missing-receipt states;
- release the worker claim, then send one payload-free terminal return;
- allow one event-driven wait for the exact finishing task only; and
- keep all monitoring, retry loops, inboxes, ledgers, transcripts, and background tools retired.

## Verification

- Focused coordination-state tests: 25 passed, 1 platform-dependent test skipped.
- Focused prompt-guard tests: 13 passed.
- Native host-boundary fault protocol: 3 passed.
- Full suite: 130 tests passed; the optional Hypothesis module and one platform-dependent symlink case were skipped.
- Source Doctor: healthy with six checks and no findings.
- Installed-package Doctor and source/install parity: verified after normal plugin-manager reinstall.

## Follow-up

- Ask the Codex host for an optional native idempotency key and authoritative mutation receipt. If supplied, use the assignment ID directly; do not build a private substitute store.
- A real service-level accepted-create/lost-response test remains a host responsibility. Keep the deterministic fake-host case as the plugin regression test.
- Contract 31 separately removes the fixed plugin-owned task cap: the user may select a count, otherwise the agent chooses the smallest useful set within host capacity. Assignment identity and sequential readback remain mandatory at every count; they prevent duplicates without turning native inventory into a new cap or monitoring loop.
