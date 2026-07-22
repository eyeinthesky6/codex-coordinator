# Retired reconciliation lane

The resident Coordinator, heartbeat, full-goal ledger, per-turn reconciliation records, inbox hash checkpoint, provider monitoring, and scheduled-task reconciliation were removed from the core architecture.

Do not load this file for normal work. Use [operations.md](operations.md) and the task-owned active board instead.

Legacy `CURRENT.md`, `tasks/`, `inbox/`, and cache records may remain on disk as preserved history. Schema 2 never treats them as active authority, scans them on SessionStart, or copies them into new claims. A separately authorised migration or purge may handle them later.
