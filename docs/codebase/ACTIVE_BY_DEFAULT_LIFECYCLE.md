# Active-by-default lifecycle — superseded

> Current pinning is narrower: [the contract-35 auto-pinning decision](2026-07-23_goal-coordinator-auto-pinning_architectural_review.md) lets only an explicitly appointed goal Coordinator pin its exact native task after goal binding and claim success. The user controls unpinning; the retained pin carries no accepting, monitoring, or project authority.

This document recorded the schema-1 decision to keep one pinned Coordinator, manage every same-repository task, retain a repository heartbeat, and expose `MANAGING`, `REPORT_ONLY`, and exclusion state.

That decision is superseded by the accepted [boundary-board architecture](2026-07-21_boundary-board-simplification_architectural_review.md).

Schema 2 is explicit opt-in and has:

- no automatic, always-on, or heartbeat-driven Coordinator task;
- no repository heartbeat or background continuation promise;
- no all-task management, operating modes, or user-exclusion ledger;
- no `CURRENT.md` authority;
- no background task creation, broad polling, repository heartbeat, automatic stop, or all-task reconciliation;
- no observer or Doctor lifecycle.

An explicitly requested, goal-scoped Coordinator remains supported as an ordinary native task. It binds the shared objective to native Goal mode, assigns only complete native-goal verticals in the shared checkout, waits on exact completion or attention events, and decides the next goal action. Short work stays in the current task or a parent-owned helper. Each assigned worker also returns exactly once at completion as a between-turn fallback. Only an explicitly unattended goal may use one temporary native thread heartbeat, removed at the first terminal or user-decision boundary. This is not the retired repository heartbeat or reconciliation loop. The reasons the schema-1 protections existed remain recorded in the decision review and Git history. Their useful invariants were replaced by one-task-first execution, per-task bounded claims, exact identity, owner-selected capacity, sparse notices, immediate user stop, external-write consent, and evidence-based stale recovery.

Do not use this file as current product guidance or restore active-by-default behavior without explicit user approval and a new architecture decision.
