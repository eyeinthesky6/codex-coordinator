# Native-task return-boundary architectural review

- **Date:** 2026-07-22
- **Corrected:** 2026-07-23
- **Status:** The contract-25 conclusion is superseded by the accepted contract-26 direction
- **Scope:** Keep an explicitly requested Coordinator useful without promising automatic task wake-up

## Scope

This review began with one concrete failure in an enabled project: a writing task created two read-only native tasks, retained the integration claim, and ended its turn after dispatch. Both tasks completed, but the creator did not resume automatically. Manual invocation was required to finish integration and release the claim.

Contract 25 drew too broad a conclusion from that incident. The evidence proves that native completion cannot be treated as an automatic wake or fan-in callback. It does not prove that an explicitly requested, goal-scoped Coordinator is invalid. The corrected design keeps that useful role while removing background monitoring and automatic-return promises.

## Evidence checked

- The exact native creator and delegated-task terminal states through supported Codex task tools.
- The schema-2 active board before and after recovery.
- Native task creation and wait semantics exposed by the host.
- The packaged SessionStart and Stop hooks.
- Capability contract 25, execution guidance, Doctor expectations, and package tests.
- The accepted boundary-board and Stop-guard architectural reviews.

No task process, scheduler, heartbeat, database, inbox, message ledger, or transcript reader is needed for the corrected contract.

## Corrected task model

### Explicit Coordinator

When the user asks one task to coordinate a bounded goal, that normal task claims the exclusive `goal-coordination` action. Its claim goal is the shared goal. It may assign two or three substantial durable verticals, each with its complete goal, exact paths and exclusive actions, verification, dependencies, and completion condition in the first assignment.

The Coordinator remains available when the user invokes it again for that goal. It is not a permanent repository role. It does not poll, wake every few minutes, run a heartbeat, demand progress reports, or promise automatic fan-in. After assignment it yields normally. When invoked again, it reads current active state and uses native task results only as needed.

### Shared checkout

Every coordinated task runs in the same primary checkout, current worktree, and current branch. This is deliberate: untracked settings, offline runners, local data, and machine-specific runtime context remain available to all verticals.

No coordinated task creates or switches a branch or worktree. Exactly one task claims `git-integration`; all other tasks edit and test only their claimed paths and do not stage, commit, push, reset, restore, stash, rebase, merge, or clean. The Coordinator may own both `goal-coordination` and `git-integration`, but it need not claim a source path unless it edits that path.

### Active state

Native Codex remains the authority for task execution, history, status, messages, and results. Coordinator state contains only bounded active claims and compact cold receipts. Tasks update their own claim only at start, real scope change, blocked-state change, and completion or stop.

Generated schema-2 `CURRENT.md` is a small human view backed by the per-task claims. It shows only the active shared goal, active task goals and ownership, status and dependencies, and Git owner. It is non-authoritative, atomically rebuilt, and contains no transcript, reasoning, prompt, tool output, inbox, command queue, task ledger, or history.

## Findings

1. **Critical — Automatic fan-in is unsupported.** Native task completion does not automatically resume an idle Coordinator, so the product must not promise that behavior.
2. **High — Removing the Coordinator role was an overcorrection.** A user-invoked Coordinator remains useful for assigning complete verticals and later integrating them on demand.
3. **High — Shared checkout is part of the product boundary.** Worktrees would hide the untracked settings and offline runners that motivated coordination in deep local repositories.
4. **High — One Git owner is required.** Multiple writers can share source paths safely only when branch and index mutations are serialized through `git-integration`.
5. **High — Monitoring remains rejected.** A completion watcher would require persistent ownership, polling, retries, and lifecycle authority.
6. **Medium — Parent-owned subagents remain useful but are not the only valid decomposition.** They fit short dependent checks; explicit durable task windows fit complete verticals.

## Accepted fixes

1. Restore the explicitly requested, goal-scoped Coordinator under the exclusive `goal-coordination` action.
2. Allow it to assign two or three complete durable verticals on the shared primary checkout and current branch.
3. Keep one `git-integration` owner and prohibit Git mutations by the other tasks.
4. Keep active updates sparse and lifecycle-based; retain native Codex as execution and history authority.
5. Keep the generated, non-authoritative active-only `CURRENT.md` view derived entirely from per-task claims.
6. State plainly that the Coordinator is available on demand and is not woken automatically.
7. Do not add an always-on/resident monitoring Coordinator, completion watcher, heartbeat, polling loop, transcript mirror, inbox, task ledger, or message relay.

## Verification status

Contract 26 encodes the corrected public contract. Focused contract and package tests must pass before release. The generated schema-2 `CURRENT.md` is implemented as a rebuildable view, not a second authority.

The original incident still provides useful negative evidence: automatic wake-up failed. It no longer supports the broader claim that complete durable verticals must be independent peers or that every combined outcome must stay inside one native task.
