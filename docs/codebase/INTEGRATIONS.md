# Integrations

## OpenAI Codex

Codex supplies native task identity, execution, messages, status, and transcripts. Coordinator consumes only an exact native thread UUID supplied when a task publishes its own claim. It never creates, pins, wakes, archives, or polls tasks automatically.

Peer collision notices use the supported native task messenger only after same-repository and exact-recipient checks. The message is non-executable and grants no authority.

SessionStart remains subject to Codex hook trust. It reads only a bounded project marker and launches no process.

## Git

Git identifies the repository and primary worktree. The skill resolves the first worktree from `git worktree list --porcelain`; the state helper itself receives the already resolved project root.

The board does not create branches, worktrees, commits, pushes, merges, or pull requests. With multiple writers, one task owns the `git-integration` action. Direct commit/push is the default for one owner; PRs are optional policy.

## GitHub

GitHub hosts source, CI, releases, Discussions, security reporting, and the static site. It is not a runtime dependency or a surface Coordinator monitors automatically.

Current provider settings, checks, protections, releases, and PR state can change independently. Read them through their owning interface when the user's task specifically requires them.

## Mission Control

There is no schema-2 Mission Control integration or runtime in the base package. A future observer would require a separate package and must use only the public board, start manually, remain read-only, and have no private Codex, Doctor, model, task, provider, schedule, or write integration.

## Doctor and plugin manager

Doctor reads only files inside one installed plugin root and runs no child process. It reports compatibility. The normal plugin manager owns update, reinstall, and rollback.

## Network and external services

The schema-2 core has no service, database, telemetry, account, or network call. Enabling the board grants no permission to use providers, deploy, publish, spend, change a database or environment, or modify a schedule.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/.codex-plugin/plugin.json`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `plugins/codex-coordinator/scripts/codex_coordinator_doctor.py`
- `plugins/codex-coordinator/skills/codex-coordinator/scripts/coordination_state.py`
