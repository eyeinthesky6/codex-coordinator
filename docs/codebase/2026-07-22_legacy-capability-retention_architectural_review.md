# Legacy capability retention architectural review

> **2026-07-23 correction:** This review's subagents-only conclusion overcorrected a native auto-resume failure. The current accepted contract supports an explicitly requested, goal-scoped Coordinator assigning complete durable verticals in one shared checkout. It still rejects automatic fan-in, polling, heartbeats, transcript mirroring, and a second task ledger. See the updated native-task return review and contract 26.

- **Date:** 2026-07-22
- **Status:** Review complete; implementation follow-up required
- **Compared baseline:** Last legacy orchestration checkpoint `926a921`, capability contract 19
- **Current source:** Schema-2 release contract `v0.4.0`, capability contract 26
- **Decision:** Retain safety invariants, not the permanent orchestration mechanisms that previously enforced them

## Scope

This review answers which parts of the complicated Coordinator implementation are essential to the simplified product.

It compares all 41 capabilities in the last legacy contract with the current boundary board, traces the hot runtime path, and identifies missing protections that could become future failures. It does not restore a permanent Coordinator, create or archive Codex tasks, alter project enablement, change automations, or modify product runtime code.

The intended product remains a repository-scoped task boundary and visibility layer:

1. native Codex tasks execute work and own transcripts;
2. each writing task publishes one small, exact ownership claim;
3. the board detects planned overlap and limits task fan-out;
4. a task releases its own claim at a terminal boundary;
5. no task continuously manages all other tasks.

## Evidence Checked

- Git status and recent history through `53fbc36` plus the current uncommitted Stop-guard correction.
- Legacy capability contract 19 at `926a921` with 41 capability entries.
- Tagged `v0.3.0` contract 9 as an earlier, smaller intermediate baseline.
- Current capability contract 25 with 21 entries.
- Legacy SessionStart, Doctor, Mission Control, bootstrap, state helper, and guidance surfaces.
- Current SessionStart, Stop guard, state helper, Doctor, lifecycle helper, execution guide, and package tests.
- The accepted boundary-board review and the one-shot Stop-guard follow-up.
- Controlled installed-package proof in ProfitPilot: zero claims, one exact claim, one Stop continuation, circuit-breaker silence, compact release receipt, and return to zero active claims.
- The live Git interaction that exposed the remaining design flaw: a tracked project marker can change when the checkout moves between branches even though the global plugin installation does not.

## Tool Baseline

The review used repository-native evidence only:

- `git status`, `git log`, `git show`, `git tag`, and `git ls-tree`;
- `rg` for entry points, privacy boundaries, claim limits, conflicts, and tests;
- direct reads of packaged JSON and Markdown contracts;
- existing unittest names and the prior full-suite result;
- the installed schema-2 board helper for the ProfitPilot lifecycle proof.

No new service, scheduler, database, task, worker, dependency, scanner, or external workspace was created.

The size change confirms the architectural change but is not treated as proof by itself:

| Surface | Legacy | Current |
| --- | ---: | ---: |
| SessionStart | 941 lines | 132 lines |
| Doctor | 681 lines | 260 lines |
| Stop lifecycle guard | absent | 211 lines |
| Deterministic board helper | present | 687 lines |
| Bundled Mission Control/bootstrap runtime | present | absent from supported core |

## Agent-Led Review

### Real runtime path

The current happy path is:

1. a five-second, read-only SessionStart hook detects an enabled schema-2 project;
2. the task loads the small skill and lists only bounded active claim records;
3. before substantial writes, the task claims exact repository-relative paths or exclusive action slugs using its native thread UUID and expected revision;
4. the helper rejects task-limit or overlap violations and rechecks after the atomic write;
5. the task completes its own work and releases its own claim to a compact cold receipt;
6. if it forgets, a one-shot Stop hook reads only that exact task's active claim and asks it to release or explicitly retain ownership.

The degraded path is intentionally small:

- disabled or absent project state is silent;
- incompatible state blocks Coordinator writes but not ordinary conflict-free work;
- malformed Stop input fails open instead of wedging the task;
- a blocked claim receives no Stop loop;
- stale ownership may be released only from exact native terminal evidence or direct user confirmation;
- plugin incompatibility is reported as update or reinstall, not repaired in place.

### What the old design got right

The old implementation addressed real failures:

- empty worker prompts and ambiguous task identity;
- uncontrolled task fan-out;
- multiple writers planning to touch the same paths;
- tiny work being promoted into durable task windows;
- stale owners being guessed from silence;
- surprise provider, release, deployment, or other external writes;
- interrupted work without a clear owner;
- unsafe cleanup and installation drift.

Those reasons remain valid. The failure was placing task creation, monitoring, provider reconciliation, Doctor, Mission Control, task reads, scheduled checks, and complete ledgers into the normal path of every task.

### Complete legacy capability disposition

`Core` means the invariant belongs in the default product. `Narrow` means keep only a smaller mechanism. `Optional` means manual or separately installed. `Host` means Codex already owns it. `Reject` means it recreates orchestration or hot-path cost.

| Legacy capability | Disposition | Retained reason and replacement |
| --- | --- | --- |
| `workerCreation` | Narrow | Create a separate native task only on direct user request and only for an independently useful peer outcome. Never create holding tasks or dependent child tasks. |
| `coordinatorRole` | Reject from durable tasks | One native task may use parent-owned subagents for a combined outcome. Do not make a durable creator depend on another native task returning later. |
| `doctorDiagnostics` | Optional | Keep a manual, read-only package compatibility check with update/reinstall as recovery. |
| `doctorProjectScan` | Reject | Project-wide scanning made Doctor another authority and repeated ordinary task reads. |
| `doctorSemanticReview` | Reject | Semantic review belongs in an explicit review task, not installation health. |
| `monitoring` | Reject | Persistent heartbeat and single-wake fallbacks caused polling turns and management latency. |
| `repositoryLifecycle` | Core, redesigned | Keep explicit local opt-in and immediate disable, but move operational enablement outside Git-tracked branch content. |
| `taskCoverage` | Reject | Not every same-repository task needs management. Only tasks that publish claims participate. |
| `taskExclusions` | Narrow | A direct user stop always wins; no managed-by-default set requires an exclusion ledger. |
| `pauseBehavior` | Narrow | Disabled means silent normal Codex operation. No Coordinator mode machine is needed. |
| `idleBehavior` | Reject | Never retain a pinned, accepting Coordinator when no goal exists. |
| `userStateReporting` | Narrow | Provide compact on-demand enabled/active/conflict status, not mode text in every answer. |
| `deliverySummary` | Narrow | Each task reports its own outcome, changed files, checks, and residual risk. No project-wide ledger. |
| `providerMonitoring` | Reject | Provider checks happen only in tasks whose requested outcome needs them. |
| `providerMutationConsent` | Core invariant | Retain exact target, advance disclosure, current consent, and immutable-target revalidation without provider reconciliation machinery. |
| `scheduledTaskReconciliation` | Reject | Schedules are separate Codex automations; the board neither owns nor reconciles them. |
| `modelDefault` | Host | Codex and the user own model choice. The board must not mirror it. |
| `reasoningDefault` | Host | Codex and the user own reasoning level. The board must not mirror it. |
| `registrationDelivery` | Core | One exact native UUID and a complete first-turn assignment prevent ambiguous or empty ownership. |
| `workerGranularity` | Core | Durable tasks are only for substantial, independently useful lanes. |
| `microtaskExecution` | Core | Keep small checks, formatting, narrow fixes, and routine follow-ups in the current task or a parent-owned subagent. |
| `parallelWorkerTarget` | Core | One task is default; three is the normal limit; a direct user decision is needed above it; twelve is a hard limit. |
| `stateTool` | Core | Deterministic validation, bounded records, lock, expected revisions, atomic writes, overlap checks, and fail-closed mutations are essential. |
| `subagents` | Host/narrow | Parent-owned subagents can reduce visible task windows, but they do not become durable board owners unless they independently write shared project state. |
| `operationsGuidance` | Narrow | Keep short, action-specific guidance. Do not reload a full operating manual for ordinary work. |
| `coordinationReadCache` | Reject | A maximum of twelve small active records is cheaper and safer than another inbox/hash/checkpoint state layer. |
| `nativeTaskReads` | Narrow | Use one exact native read only for user-requested status or evidence-based stale recovery. No all-task polling or transcript mirror. |
| `continuationGuarantee` | Host/narrow | Parent-owned subagents return through the host to their parent. Separate native tasks own their own outcomes. The Stop guard covers claim housekeeping, not cross-task resumption. |
| `archivedRecovery` | Core, narrow | Direct user evidence or exact native terminal state may release a stale claim. UI archive is not inferred from silence. |
| `externalWriteDisclosure` | Core | Retain exact advance notice and authority before provider, publication, deployment, release, message, or other external writes. |
| `missionControlLifecycle` | Reject from core | If usage later justifies it, ship a separate, manually started, read-only observer with no task authority. |
| `subagentDispatch` | Host | Use host subagents only when explicitly helpful; do not create a Coordinator dispatch policy or ledger. |
| `pythonRuntimeBootstrap` | Reject | Never install or discover runtimes from SessionStart. A broken dependency gets a simple installation error. |
| `lifecycleCleanup` | Core, manual | Keep dry-run-first migration, exact targets, history-preserving archive, and rollback. Never put cleanup in SessionStart. |
| `globalUninstall` | Optional | Provide a bounded manual uninstall/cleanup operation. No drive scans or project-wide background inventory. |
| `worktreeSelection` | Core invariant, redesigned | All worktrees of one repository must see one local board. The board does not choose or create worktrees. |
| `waitingClassification` | Core invariant | Classify blocked/stale only from explicit dependency or native evidence, never silence, elapsed time, or `idle`. |
| `delegationDecision` | Narrow | Keep the simple rule: one task by default; dependent checks use parent-owned subagents, while a durable peer requires both direct user request and an independently useful result. Do not record a decision ledger. |
| `taskTitlePolicy` | Reject | Native titles are user/task UI concerns. Do not spend turns renaming tasks. |
| `historicalTaskReconciliation` | Reject | Native task history remains in Codex. The board contains current ownership only. |
| `taskLifecycle` | Narrow | Retain claim/update/release and explicit handoff boundaries. Remove automatic pinning, renaming, native archive, and manager-owned lifecycle. |

### Must-have core, stated positively

The simplified product needs these ten things:

1. **Git-independent local project state.** Enablement, active claims, and compact receipts must not move backward and forward with branches or commits.
2. **One repository identity shared by all worktrees.** Resolve Git's common directory and keep one board there.
3. **Exact native task identity.** One claim per exact thread UUID; no title or fuzzy matching.
4. **Bounded ownership.** Exact relative paths and exclusive action names, with deterministic overlap detection.
5. **Task-count control.** One task by default, three normal, twelve hard, with direct user authority above three.
6. **Atomic, bounded state.** Size limits, schema checks, link containment, locking, expected revisions, and crash-safe writes.
7. **Private-content exclusion.** Never store or inspect prompts, reasoning, transcripts, tool output, messages, or private Codex databases.
8. **Terminal release backstop.** Each task releases itself; Stop checks only that task once and has a circuit breaker.
9. **Evidence-based stale recovery.** Direct user confirmation or exact native terminal evidence; never infer from silence or age.
10. **User authority.** Immediate stop, exact external-write disclosure, and no automatic task, provider, schedule, Git, or native lifecycle mutation.
11. **No cross-task return dependency.** Native durable tasks are independent peers. Dependent parallel checks use parent-owned subagents that return to the same task, or run sequentially when subagents are unavailable.

Manual migration/cleanup and a read-only compatibility check are also necessary product operations, but they are not hot-path coordination.

## Findings

### P0 — Runtime state still moves with Git

The current global plugin installation is correctly independent of project Git. The current project runtime is not fully independent: `coordination_enabled` and schema live in tracked `.codex/coordination/project.yaml`, while repository guidance lives in tracked `AGENTS.md`. Branch changes can therefore expose old, absent, disabled, or incompatible project state.

The live ProfitPilot interaction demonstrated this directly. The installed helper briefly saw schema 1 during concurrent Git activity, then schema 2 after the checkout settled. This is unacceptable as the final architecture even though the controlled lifecycle proof later passed.

Operational state should not move with code history. At most, a repository may carry optional, non-authoritative documentation that the tool is supported. Local enablement and active ownership must remain local.

### P0 — The retained safety kernel is smaller than the old Coordinator

Exact identity, claims, conflicts, limits, atomic mutation, privacy, release, evidence-based stale recovery, and user authority cover the original user problem. None requires a resident manager, heartbeat, Doctor scan, Mission Control, provider reconciliation, schedule reconciliation, or full ledger.

### P1 — Cold receipts need a hard retention bound

Receipts are compact and separate from the active board, which is correct. They can still grow forever. Native Codex is already the task-history authority, so the product should cap cold receipts by count or age during an explicit release/maintenance operation. No watcher is needed.

### P1 — Natural activation proof remains distinct from script proof

The installed ProfitPilot script proof demonstrates the exact state helper and Stop guard. A task that began before enablement will not retroactively have a claim. The next newly started or resumed substantial-write task must show that it loaded the current hook/skill, created its own bounded claim, and released it. Do not create a task only to manufacture this evidence.

### P0 — Native tasks cannot safely be dependent children

ProfitPilot exposed a second lifecycle gap: one task created two correct read-only native tasks, retained the integration claim, then sent its final answer immediately after dispatch. Both other tasks completed, but native completion did not wake the idle creator. The board correctly preserved ownership, yet the goal stopped before synthesis.

An initial correction required the creator to keep its turn active and wait on exact native task IDs. That remains guidance-only and cannot make a completed native task resume an already idle creator. Manual wake-up is not an acceptable product path, and adding a resident watcher would recreate the rejected orchestrator.

The supported boundary is therefore narrower: separate native tasks are independent peers that report their own useful outcomes. Work that must return to a creator uses parent-owned subagents inside that creator's live turn; the host returns those results automatically. If subagents are unavailable, the work remains sequential in one native task.

### P2 — Manual Doctor remains useful but must stay small

The current Doctor validates package shape and hook compatibility and reports update/reinstall. That is useful. Project scans, semantic review, self-repair, rollback engines, managed-file mutation, and optional-runtime authentication are not.

## Recommended Fixes

### 1. Move runtime authority to Git's common local directory

Use a plugin-owned directory under the repository's resolved Git common directory, for example:

```text
<git-common-dir>/codex-coordinator/
  project.json
  active/<thread-uuid>.json
  archive/<compact-receipt>.json
```

Why this location fits:

- branch checkout, reset, merge, rebase, and commit do not touch it;
- all linked worktrees resolve the same common directory;
- `git clean` and source packaging do not include it;
- cloning or deleting the repository naturally requires an explicit local re-enable;
- the plugin remains globally installed and independently versioned.

The resolver must stay bounded, avoid child processes in hooks, reject links or path escape, and support normal repositories plus linked worktrees. Tests must cover branch switching, two worktrees, absent state, incompatible local schema, and removal/re-clone.

### 2. Remove tracked operational authority

After the local-state implementation is proven:

- stop using tracked `coordination_enabled` as runtime authority;
- stop storing active/archive paths in tracked branch content;
- remove the exact installed task-board block from project `AGENTS.md` when SessionStart can supply the enabled-project instruction;
- keep any committed project file optional and informational only, or remove it entirely;
- migrate one project at a time and preserve the old marker in the external legacy archive.

### 3. Retain the existing safety kernel

Do not weaken current UUID validation, task limits, path/action overlap, case-insensitive matching, link containment, bounded reads, locks, expected revisions, atomic replacement, one-shot Stop circuit breaker, external-write consent, or evidence requirement for stale release.

### 4. Bound cold receipts without a background job

On release or explicit maintenance, keep a small maximum such as the newest 100 compact receipts or a user-configured shorter window. Never store full results or transcript content. Overflow cleanup must be deterministic and must never touch active claims.

### 5. Keep optional surfaces outside the core

- Mission Control: separate install, manual start, read-only, no task authority.
- Doctor: manual package compatibility only.
- Native monitoring and schedules: Codex-owned and explicitly requested.
- Pull requests: optional; direct commits remain valid.

### 6. Keep dependent parallel work inside one native task

Do not use native task creation for work that must return to the creator. Use parent-owned subagents so the host returns results to the same task, or work sequentially when subagents are unavailable. Separate native tasks require a direct user request, own independent outcomes, and never leave a creator claim waiting for later resumption. This rule needs no persistent state, message ledger, Coordinator task, or background watcher.

## Verification

Current source evidence already covers:

- one-task default and active-task limits;
- exact UUID, path, action, and revision validation;
- overlap detection before and after atomic write;
- compact active records and cold receipts;
- no transcript/private-Codex coupling in core hooks;
- bounded SessionStart and one-shot Stop behavior;
- read-only Doctor with reinstall/update recovery;
- no bundled supported Mission Control runtime;
- optional pull requests and direct Git workflow.

The corrected full discovery passed 93 tests with two expected environment/optional-dependency skips. The installed ProfitPilot controlled lifecycle proof passed and returned the board to zero active claims.

The Git-independent state option is not implemented. The user instead selected a stricter shared-checkout contract for `v0.4.0`: all coordinated tasks remain on the current branch and do not create or switch branches or worktrees while the goal is active. A future design that intentionally supports branch switching would require:

1. unit tests for normal repositories and linked worktrees sharing one common board;
2. a test that branch checkout between schema-1, schema-2, and marker-absent commits does not change local enablement or active claims;
3. migration tests that preserve tracked legacy state and do not overwrite dirty files;
4. SessionStart and Stop tests using only the common local state;
5. full unittest discovery, JSON parse, Python compile, and `git diff --check`;
6. a real project trial after the active product task reaches a stable Git boundary.

## Follow-Up

Do not claim that coordination survives an intentional branch switch. Treat Git-independent runtime state as a future, separately approved capability rather than a `v0.4.0` release gate. Keep the current tracked-marker implementation and its schema checks as the supported shared-checkout contract.

Do not reintroduce the rejected capabilities while solving branch stability. Branch stability is a state-location problem, not a reason for a resident Coordinator, heartbeat, reconciliation loop, task inventory, or second transcript authority.
