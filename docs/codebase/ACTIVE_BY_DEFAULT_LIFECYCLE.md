# Active-by-default lifecycle — superseded

This document recorded the schema-1 decision to keep one pinned Coordinator, manage every same-repository task, retain a repository heartbeat, and expose `MANAGING`, `REPORT_ONLY`, and exclusion state.

That decision is superseded by the accepted [boundary-board architecture](2026-07-21_boundary-board-simplification_architectural_review.md).

Schema 2 is explicit opt-in and has:

- no automatic, always-on, or heartbeat-driven Coordinator task;
- no repository heartbeat or background continuation promise;
- no all-task management, operating modes, or user-exclusion ledger;
- no `CURRENT.md` authority;
- no automatic task creation, wake, stop, resume, or reconciliation;
- no observer or Doctor lifecycle.

An explicitly requested, goal-scoped Coordinator remains supported as an ordinary native task. It assigns complete verticals in the shared checkout and reads current state only when invoked. The reasons the schema-1 protections existed remain recorded in the decision review and Git history. Their useful invariants were replaced by one-task-first execution, per-task bounded claims, exact identity, task caps, sparse notices, immediate user stop, external-write consent, and evidence-based stale recovery.

Do not use this file as current product guidance or restore active-by-default behavior without explicit user approval and a new architecture decision.
