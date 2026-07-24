# Boundary invariant bug audit

> **2026-07-23 receipt follow-up:** The product-side assignment identity, terminal return, and deterministic fault-injection coverage are implemented in [the assignment-receipt review](2026-07-23_terminal-return-idempotency_architectural_review.md). A host-enforced transaction remains unavailable, so the contract stops rather than retrying an ambiguous mutation with no visible receipt.

Status: fixes implemented and locally verified
Date: 2026-07-23

## Scope

This review checks the smallest runtime boundaries that prevent Codex Coordinator from starting work in the wrong task or creating invalid active-task authority. It covers the prompt-time repository guard, claim revisions, the user-approved task-limit override, native task creation authority and receipts, and their tests.

It does not add task monitoring, polling, a Coordinator loop, a second state store, transcript inspection, automatic task creation, Mission Control, Doctor repair, or a runtime dependency.

## Evidence checked

- The documented peer-notice shape in `references/messaging.md`.
- The packaged `UserPromptSubmit` registration and prompt guard.
- The schema-2 `claim_boundary` and `release_boundary` entry points.
- Deterministic prompt, state, package, Doctor, and leadership tests.
- The existing Hypothesis rule-based claim lifecycle test.
- A temporary Hypothesis-only environment using `requirements-property-tests.txt`.
- Direct reproductions of each finding before its fix.
- A 30-run local prompt-hook timing sample after the fix.
- A live native-task incident in which an apparently failed handoff and apparently failed creations all succeeded.
- The v0.3.0 task allocation, delivery, recovery, reconciliation, Doctor, and Mission Control contracts for retained-versus-retired comparison.

## Tool baseline

Hypothesis remains a test-only sidecar. It is useful here because claim, update, overlap, stale-revision, release, and invalid-input sequences have more combinations than a short example list can cover. It is installed only in the dedicated CI workflow or an isolated test environment; no plugin script imports it.

The product runtime remains Python standard-library code. Native Codex owns task placement and execution, Git owns the checkout, and the schema-2 helper owns only bounded active claims.

## Agent-led review

This was one coherent owner slice, so no additional durable task was opened. The prompt guard was traced from the packaged hook through both documented assignment forms. The state helper was traced from its public claim and release functions through revision comparison, task-limit checks, atomic writes, generated `CURRENT.md`, and compact release receipts.

One normal path and one failure path were exercised for each changed owner. The existing generated state machine continued to compare canonical claims and the derived current view after every action.

## Findings

### 1. High — the documented assignment shape bypassed the repository guard

The messaging contract emits `Kind: GOAL_ASSIGNMENT`, but the guard recognized only a standalone `GOAL_ASSIGNMENT` line. A correctly formatted Coordinator notice could therefore reach an agent in the wrong project with no prompt-time block.

Reproduction: a complete documented notice targeting a different local Git root returned no hook output.

Fix: the guard now recognizes both the compact standalone marker and the documented `Kind:` field. The message contract also requires the verified absolute local primary checkout in one `Repository:` field.

### 2. High — text truthiness could bypass the three-task approval limit

`user_approved_over_limit` was converted with `bool(...)`. The string `"false"` therefore became `True`, allowing a fourth active claim without an actual boolean approval value.

Reproduction: three normal claims followed by a fourth claim with `user_approved_over_limit="false"` produced four active claims and stored `limitOverride: true`.

Fix: the canonical claim entry point now accepts only an actual boolean before it evaluates the task limit.

### 3. Medium — Python numeric equality weakened revision typing

Python treats `False == 0`, `0.0 == 0`, and `True == 1`. The claim API therefore accepted boolean or floating-point revision inputs when their value matched the current integer revision. The release API likewise accepted `True` for revision 1.

Reproduction: `False` created revision 1 and `True` updated it to revision 2.

Fix: claim revisions must be non-negative exact integers, and release revisions must be positive exact integers. Booleans are rejected explicitly.

### 4. Medium — a valid marker after 8 KB was not inspected

The input payload was bounded to 1 MiB, but marker detection searched only the first 8,192 prompt characters. A long but valid delegation preface could place the assignment marker outside that smaller window and bypass the repository check.

Reproduction: 8,200 characters followed by a wrong-repository assignment returned no hook output.

Fix: marker detection now scans the already bounded prompt.

### 5. High — an ambiguous native task error was treated as definite failure

The native interface returned `No handler registered` after a follow-up send and after local task creation. Live task readback proved that the follow-up had started the reused Coordinator and that the supposedly failed creation calls had also created their tasks. The caller nevertheless reported that nothing was created and used a fallback. The reused Coordinator then created its own workers, multiplying five writer tasks from one requested decomposition.

The plugin cannot repair the host's missing result handler, but its decision contract was incomplete: it did not say that an error can arrive after a native mutation succeeds.

Fix: a timeout, transport failure, missing handler, or similarly ambiguous mutation result is now an unknown outcome. The acting task performs one immediate unfiltered native readback keyed by repository, recipient, and source relationship. It cannot resend or create fallback tasks until readback proves the original operation did not happen. An unresolved outcome is reported to the user rather than retried.

### 6. High — the three-task limit ran after native task creation

The schema-2 helper enforces the normal limit when a task publishes its claim. A native task window is created before that claim exists. In the live incident, the board still contained only the goal Coordinator while five native writer tasks had already been opened.

Fix: the exact goal Coordinator now performs one unfiltered native inventory immediately before every creation. It counts itself, active claims, and native non-terminal tasks already participating in the goal, including created tasks that have not claimed yet. The board limit remains a final state guard; it is no longer described as sufficient creation control.

### 7. High — more than one task could create workers for the same goal

A requester attempted to hand work to the active Coordinator. When the native send returned an ambiguous missing-handler error, the requester created fallback workers. The handoff had actually succeeded, so the Coordinator independently created its own workers. The one `goal-coordination` claim prevented a second claim owner but did not explicitly reserve native task creation to that owner.

Fix: only the exact active `goal-coordination` owner may reuse or create coordinated durable workers. A delivery failure does not transfer authority, and a requester or worker never creates fallback workers for that coordinated goal.

### 8. Medium — broad decomposition language was treated as a numeric override

The user asked for separate threads by vertical. The acting Coordinator described that as explicit approval for exactly three writer tasks, even though the user did not specify a count or approve exceeding the normal three-task total after including the Coordinator.

Fix: three active durable tasks now explicitly includes the Coordinator. A request to split work permits decomposition only. Going above three still requires a direct user decision about the higher count and the exact boolean override.

### 9. Medium — creation receipts did not validate user-visible identity

The incident produced duplicated generic titles and one task whose title contained its full assignment body. That made related tasks hard to distinguish and was direct evidence that creation success alone was being treated as a complete receipt.

Fix: creation is sequential. After each create, the Coordinator reads back the exact returned task and verifies source relationship, repository working directory, complete assignment, and a short distinct human title. A generic, duplicated, or assignment-sized title may be renamed once after identity is proven. A failed rename never creates a replacement.

## What v0.3.0 already knew

The simplification did remove a thin but important control seam that v0.3.0 had documented:

- one registered Coordinator had sole task-creation authority;
- an unreachable Coordinator did not permit a possible duplicate Coordinator or fallback worker;
- native capacity and same-area reuse were checked before every creation;
- tasks were created once, bound to the exact returned native identity, then read back;
- generic native titles were corrected after exact identity verification; and
- `idle` or `notLoaded` did not make a task spare capacity for unrelated work.

Those are creation-time invariants, not orchestration. They are now restored in the smaller schema-2 contract.

v0.3.0 did not fully solve the current host failure mode. Its send lane allowed a retry, which can duplicate a mutation when the host accepts it and loses only the result. Its later reconciliation machinery could discover contradictions, but only after extra work and delay. The current contract therefore keeps the stricter no-blind-retry rule.

## What remains retired

The incident does not justify restoring v0.3.0 as a whole. These mechanisms stay out of the hot path:

- mandatory full-turn reconciliation records;
- heartbeats or scheduled status checks;
- durable inboxes, hash acknowledgements, and resume queues;
- task transcript, reasoning, prompt, or tool-output mirrors;
- Mission Control task receipts or task authority;
- Doctor scanning, findings, repair, or rollback; and
- automatic fan-out or permanent Coordinator monitoring.

The correction is one pre-mutation inventory and one post-mutation receipt per requested task creation. It adds no background work when no task is being created.

## Recommended fixes

All confirmed fixes in this slice are implemented in the existing canonical owners:

- require one absolute local `Repository:` in every actionable assignment;
- recognize both supported assignment markers across the bounded prompt;
- reject absent, relative, remote-only, duplicated, unverifiable, or mismatched assignment repositories;
- require exact revision integers; and
- require an actual boolean for the task-limit override.
- reconcile one ambiguous native mutation by deterministic assignment ID with a single readback and never retry blindly;
- reserve coordinated durable-task creation to the exact goal Coordinator;
- count native task capacity immediately before each creation, including unclaimed created tasks;
- create sequentially and validate exact placement, assignment, and title receipts; and
- require same-goal context for reuse and a direct numeric decision for an over-limit plan.

No background safety mechanism is recommended. These checks run only when a prompt is submitted or a claim is mutated.

## Verification

- Focused prompt guard: 10 tests passed.
- Focused coordination state: 22 tests passed, 1 platform-dependent symlink test skipped.
- Focused leadership, package, and Doctor contracts: 38 tests passed.
- Hypothesis: 100 generated claim-lifecycle programs with up to 25 actions each passed, plus 100 generated invalid revision and approval examples.
- Dependency-free full suite: 121 tests ran successfully after the added matching-notice test, with the property module and one platform-dependent symlink test skipped when their prerequisites were absent.
- Full suite in the isolated Hypothesis environment: 123 tests ran successfully after the added matching-notice test, with only the platform-dependent symlink test skipped.
- Prompt guard timing, 30 local runs each: ordinary prompt median 49.15 ms and p95 58.08 ms; matching assignment median 53.39 ms and p95 60.13 ms.
- `git diff --check` passed before final verification.

## Follow-up

- The source repository remains disabled, so these changes do not activate coordination here.
- The installed plugin will not gain the new hook behavior until the package is released or installed and the host trusts the changed hook registration.
- Native task creation is host-owned. Contract 30 now provides deterministic assignment identity, one exact receipt readback, and at-most-once decision semantics in the plugin. It still cannot transactionally intercept or cancel a native create call. Hard host enforcement would require an idempotency key, precondition or capacity token, and an authoritative creation receipt; rebuilding that through private Codex state or a monitor would recreate the rejected architecture.
- The guard deliberately validates the supported assignment contract; it is not a general natural-language intent classifier.
- Hook payloads above the existing 1 MiB safety limit remain ignored because they cannot be parsed safely. That is a bounded malformed-input posture, not a normal assignment path.
- Keep Hypothesis test-only. Its value is generated state and input coverage, not runtime coordination.
