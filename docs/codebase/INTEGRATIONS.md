# Integrations

## OpenAI Codex

Codex supplies native task identity, execution, messages, status, goals, event waits, task pins, thread heartbeats, and transcripts. Coordinator consumes only exact assigned task UUIDs and the results needed for a goal decision. It never runs a custom watcher, archives tasks, polls all-task status, or copies transcripts. The only pin action is one best-effort native pin on the exact appointed goal Coordinator after goal binding and claim success; workers and project enablement never pin, and only the user unpins.

Peer collision notices use the supported native task messenger only after same-repository and exact-recipient checks. The message is non-executable and grants no authority. An explicitly appointed goal Coordinator may also send one bounded in-repository assignment to a suitable related local task. It waits on exact native task completion or attention events and decides the next step. The worker still sends one terminal `RESULT_READY` after releasing its claim as a between-turn fallback. Neither notice grants external or destructive authority.

For an explicitly unattended goal only, the Coordinator may create one temporary Codex heartbeat attached to its own task when an event wait cannot remain open. The heartbeat checks only the exact known assignments and is deleted at the first completed, stopped, user-decision, or unverifiable-goal boundary. Project enablement creates no automation, and the repository stores no automation prompt, ID, result, or schedule.

SessionStart and UserPromptSubmit remain subject to Codex hook trust. SessionStart reads a bounded project marker and counts only recognized pending-notice filenames for the exact current task UUID; it reads no notice body and launches no process. UserPromptSubmit reads only the pending prompt and current working directory; it requires every actionable `GOAL_ASSIGNMENT` or `RESULT_READY` to contain one valid assignment ID and a local repository that matches the task's Git worktree. A durable assignment must also request native Goal mode and contain one bounded objective; after validation the hook supplies the system instruction that makes the receiving task call `get_goal` and safely bind `create_goal` before repository work.

Codex does not currently expose a host-enforced idempotency key or transactional receipt for task creation or message delivery. The plugin therefore derives a deterministic assignment ID and performs one exact readback after an ambiguous result. It never blindly retries. If a notice readback has no receipt and the exact recipient UUID is known, one standard-library helper records routing metadata only for that assignment or terminal return. Normal delivery writes nothing; later verified receipt or recipient action deletes the record. If task creation returns no identity and readback finds none, no safe recipient exists and no placeholder record is created. The fallback has no payload, watcher, scheduler, acknowledgement, or wake authority. Fault-injection tests cover accepted-create/lost-response, accepted-send/lost-response, and known-recipient no-receipt behavior.

## Proposed cross-harness adapters

The current release supports Codex only. The [cross-harness portability review](2026-07-23_cross-harness-portability_architectural_review.md) proposes a sibling portable package with a host-neutral board core and thin adapters: Claude Code first, Hermes Agent second, and OpenClaw third.

Agent Skills installation alone proves discovery, not workflow compatibility. Each adapter must separately prove exact native identity, same-checkout execution, bounded lifecycle hooks, result return without polling, and no transcript or host-task-store ingestion before it is listed as supported.

## Git

Git identifies the repository and primary worktree. The skill resolves the first worktree from `git worktree list --porcelain`; the state helper itself receives the already resolved project root.

The board does not create branches, worktrees, commits, pushes, merges, or pull requests. Coordinated tasks share a branch established before parallel writing. Each task may commit only its reviewed exact files while preserving foreign staged work. `git-integration` is a legacy advisory action, not a durable owner. Direct commit/push is the default; PRs are optional policy.

## GitHub

GitHub hosts source, CI, releases, Discussions, security reporting, and the static site. It is not a runtime dependency or a surface Coordinator monitors automatically.

Current provider settings, checks, protections, releases, and PR state can change independently. Read them through their owning interface when the user's task specifically requires them.

## Optional observers

The optional schema-2 Mission Control is a manual localhost view, not a Coordinator integration. It reads one explicitly named project's active board through the existing state helper and exposes no private Codex, Doctor, model, task, provider, schedule, or write integration. No hook or lifecycle command starts it.

## Doctor and plugin manager

Doctor reads only files inside one installed plugin root and runs no child process. It reports compatibility. The normal plugin manager owns update, reinstall, and rollback.

## Network and external services

The schema-2 core has no service, database, telemetry, account, or network call. Enabling the board grants no permission to use providers, deploy, publish, spend, change a database or environment, or modify a schedule.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/.codex-plugin/plugin.json`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_prompt_guard.py`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `plugins/codex-coordinator/scripts/codex_coordinator_doctor.py`
- `plugins/codex-coordinator/skills/codex-coordinator/scripts/coordination_state.py`
