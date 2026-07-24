# Pull-first inter-agent task communication architectural review

Status: accepted and implemented in capability contract 38.

> **2026-07-24 live-format and language correction:** ProfitPilot produced a `RELEASED` communication whose underlying
> claim release was valid but whose message appended schema and claim revisions, granted edit
> permission, and relayed unrelated production/map status. The prompt hook previously guarded only
> assignments and terminal returns, so instruction-only inter-agent formatting could drift. The existing
> contract is now enforced at prompt time: inter-agent task communication uses the enabled local project ID, plain task
> UUIDs, one boundary, and one factual `Paused:`, `Blocked:`, or `Resolved:` effect. Valid communication
> receive a non-executable system reminder. The guard reads no active claim and adds no inbox,
> acknowledgement, monitor, or second authority. The neutral header is now `Inter-agent task
> communication — no user action needed.`; the older task-boundary wording is rejected.

## Scope

Reduce inter-agent task communication that interrupts active work without losing the small amount of
coordination needed to avoid duplicate work and unblock real dependencies. Tasks should be able to
finish their assigned vertical without receiving running commentary from other tasks.

## Evidence Checked

- Schema 2 already stores one compact active claim per task and generates an active-only `CURRENT.md`.
- Claims already change only at start, material scope change, blocked-state change, and terminal release.
- Native Codex owns task execution, status, messages, goals, and transcripts.
- The current messaging contract permits assignment, terminal return, actual collision, dependency,
  and release communication, and already forbids registration, acceptance, progress, thanks, and acknowledgements.
- The existing `pending-notices/` compatibility record is created only after a native assignment or terminal return
  has no visible receipt. It contains routing identity only and is not a normal message channel.
- ProfitPilot's current board had two active claims. Nothing in those records required periodic inter-agent
  updates or a broadcast path.

## Tool Baseline

Reuse the active claim board for passive visibility and native task messages for the few events that
require immediate action. No new inbox, queue, watcher, scheduler, acknowledgement chain, transcript
copy, or message database is needed.

| Need | Existing path | Decision |
|---|---|---|
| See planned ownership | Active claims or generated current view | Pull only at a natural work boundary |
| Assign a durable lane | One `GOAL_ASSIGNMENT` | Send once to the exact worker |
| Return completed work | Native completion event plus one `RESULT_READY` fallback | Exact Coordinator only |
| Stop an actual collision | `COLLISION` | Send only after the exact hunk or command is paused |
| Declare a real blocker | Claim status plus one `DEPENDENCY` | Send only when the recipient must act |
| Resume that blocker | One `RELEASED` | Exact blocked recipient only |
| Recover failed native delivery | Routing-only pending delivery record | Keep exceptional and payload-free |

## Agent-Led Review

The review traced the skill router, execution rules, message shapes, pending-delivery fallback,
SessionStart behavior, active board, public capability contract, Doctor compatibility check, and
regression tests. This is one coupled instruction contract, so no parallel agent review was used.

The happy path is: complete assignment, independent work, natural claim updates, native completion,
one terminal return if needed. The degraded path is: actual blocked dependency or collision produces
one actionable communication; a native delivery with no receipt may leave one routing-only record.

## Findings

### 1. The board already replaces routine update messages

Title, goal, planned paths, dependencies, and active or blocked state are available without waking
another task. Repeating those facts in native messages adds attention cost without new authority.

### 2. A general inbox would restore the removed coordination burden

A useful general inbox needs readers, delivery state, acknowledgements, cleanup, stale handling, and
often a monitor. It would compete with native Codex messages and the active board. The existing
pending delivery record avoids that architecture because it stores only an unconfirmed routing fact on a rare
failure path.

### 3. Allowed message kinds still need an action gate

Naming allowed kinds is not enough. Agents may describe a progress update as a dependency or send a
release to everyone. Each communication must be justified by one exact recipient action that cannot wait
until that recipient's next natural board read.

### 4. Coordinators must not become progress relays

The Coordinator needs terminal or attention events to make goal decisions. It does not need to
forward one worker's status to other workers, ask for estimates, or publish periodic summaries.

### 5. Format drift can turn a factual release into an instruction

Live use showed that a correct claim transition can still produce a bad message. Schema labels and
claim revisions become stale immediately, “you may” incorrectly grants authority that belongs to the
recipient's existing goal and claim, and unrelated production or map status wakes the task with no
necessary action. Instruction text alone did not reliably prevent this. The bounded prompt guard now
rejects that shape before the agent treats it as a coordination event.

## Recommended Fixes

1. Define the board as the pull-first passive visibility path.
2. Require a three-part message gate: exact recipient, exact action needed now, and information that
   cannot safely wait for the next natural board read.
3. Ban start, claimed, working, percent-complete, test-running, estimate, FYI, summary, availability,
   registration, acceptance, thanks, acknowledgement, and status-check messages.
4. Keep worker completion as one native event plus at most one exact `RESULT_READY` fallback.
5. Send `RELEASED` only to a task currently blocked on that exact dependency or collision.
6. Keep claim writes at natural boundaries and forbid notification-on-claim-change behavior.
7. Keep the `pending-notices/` compatibility path exceptional, routing-only, and unavailable for ordinary updates.
8. Keep inter-agent headers machine-small: plain project ID, plain sender and recipient UUIDs, one boundary,
   and one factual effect. Never carry schema versions, claim revisions, permission, or project status.

## Verification

- Capability contract 38 names pull-first, action-only inter-agent task communication.
- Guidance and operating tests require the exact message gate and forbidden update classes.
- Prompt-guard tests reject annotated IDs, permission grants, assignment fields, disabled or
  mismatched projects, and unrelated status while accepting the factual non-executable form.
- Package tests prove that a pending delivery record remains limited to failed assignment or terminal return.
- Existing workflow, fault-injection, privacy, message-shape, and full package tests continue to pass.
- Reinstall verification compares source and installed package files by SHA-256 and runs installed Doctor.

## Follow-Up

Observe one real ProfitPilot coordinated goal. Routine worker progress should produce no inter-agent message.
The Coordinator should receive only completion or a genuine request for attention. If agents still
send status chatter, capture the exact message and strengthen the relevant instruction; do not add an
inbox, polling loop, or background monitor as the first response.
