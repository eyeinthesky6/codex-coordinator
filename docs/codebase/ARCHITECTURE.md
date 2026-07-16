# Architecture

Codex Coordinator adds a small coordination layer around Codex's native tasks. It does not run a daemon, own Git operations, or replace Codex agents.

## Main flow

1. A user invokes `$codex-coordinator` for work that needs coordination.
2. The skill checks the repository marker and current task context.
3. For meaningful parallel or cross-task work, it lazily creates the repository-scoped marker, local current-state record, and only the task records that are needed.
4. The coordinator assigns bounded ownership and uses Codex's native task messaging tools for live communication.
5. Durable repository-local records preserve the handoff when a task pauses, compacts, or restarts.
6. On SessionStart, the Python hook reads bounded state from the primary worktree and emits a short context block. It does not change repository files.

## State boundary

- `.codex/coordination/project.yaml` is the stable, trackable discovery marker.
- Mutable ownership, task, and handoff records stay local to the checkout and are ignored by Git.
- A project ID and current epoch guard cross-task routing. Messages without the expected repository identity and recipient are not actionable.
- Git worktrees isolate files and branches; Coordinator records ownership and handoffs. These are complementary controls.

## Hook safety boundary

The hook validates and bounds marker values, text size, table rows, Git output, and emitted context. It uses a bounded Git query to find the primary worktree, treats malformed or truncated state as unknown, and never turns recovered text into authority.

## What the plugin does not own

- Git commits, merges, branches, or worktree lifecycle.
- Deployment, database, environment, or provider permissions.
- Cross-machine state synchronization.
- Application locks or enforcement.

## Evidence

- `plugins/codex-coordinator/skills/codex-coordinator/SKILL.md`
- `plugins/codex-coordinator/skills/codex-coordinator/references/operations.md`
- `plugins/codex-coordinator/skills/codex-coordinator/references/recovery.md`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `.gitignore`
