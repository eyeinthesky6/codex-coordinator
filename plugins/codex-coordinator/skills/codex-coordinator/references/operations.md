# Boundary-board operations

This is a small router, not a reconciliation loop. An explicitly requested Coordinator is one normal, goal-scoped task that pins itself after taking the goal, assigns bounded work, waits on exact native task events, and decides the next step when work completes or needs attention. It never scans every task, asks for progress, or changes the user's pin after the goal ends.

- To list, create, update, or release task claims, read [execution.md](execution.md).
- To send or receive assignment, terminal-return, collision, or dependency communication, also read [messaging.md](messaging.md).
- If one native assignment or terminal return has no visible receipt after its single readback, use only the [routing-only failed-delivery fallback](execution.md#failed-delivery-fallback).
- To recover a stale or interrupted claim, read [recovery.md](recovery.md).

Do not read archived receipts during ordinary work. Do not scan native task history, providers, pull requests, or schedules merely because the board is enabled. Inspect or change one exact temporary thread heartbeat only when the user requested unattended supervision for the current goal.

The authoritative active ownership state is the set of per-task JSON claims. Generated schema-2 `CURRENT.md` is a small active-only human view rebuilt from those claims. This is the pull-first visibility path: another task reads it only when starting substantial work, approaching a known shared boundary, handling a real blocker, or responding to an explicit user request. A claim change never sends or justifies a message. `CURRENT.md` is not an inbox, command surface, task ledger, memory store, or second authority. A routing-only pending delivery record captures an unconfirmed native delivery; it never grants work authority or carries task content.

Before sending any inter-agent task communication, identify one exact action the recipient must take now and why it cannot safely wait for that task's next natural board read. If either answer is missing, send nothing and keep working. Never relay routine progress between workers.
Normal user replies come from the task doing the work. Mention another owner only when it explains an overlap, dependency, or handoff. Keep internal thread IDs out of ordinary user chat unless the user asks for diagnostics.
