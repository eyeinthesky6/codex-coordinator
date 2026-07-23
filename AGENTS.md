# Repository guidance

Codex Coordinator is a small, dependency-free Codex plugin. Keep changes narrow, public-safe, and rooted in the existing package contract.

## Source of truth

- Plugin metadata: `plugins/codex-coordinator/.codex-plugin/plugin.json`
- Coordination behavior: `plugins/codex-coordinator/skills/codex-coordinator/`
- SessionStart hook: `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- Marketplace entry: `.agents/plugins/marketplace.json`
- Behavior and package checks: `tests/`

Read the relevant skill references and tests before changing protocol fields, ownership rules, routing, recovery, or hook output. Preserve existing contracts unless the change explicitly updates them and their tests.

## Working rules

- Keep the runtime on the Python standard library unless a real requirement justifies a dependency.
- Keep the SessionStart hook read-only, bounded, and free of network access.
- Do not add credentials, private task messages, user paths, or a project's live `.codex/coordination/` state.
- Keep mutable coordination state local. Only `.codex/coordination/project.yaml` is designed to be committed in an enabled project.
- Do not copy the Coordinator operating manual into projects that use the plugin.
- Update public documentation and tests with user-visible behavior.
- Avoid unrelated cleanup and generated audit artifacts.

## Validation

Run from the repository root:

```shell
python -m unittest discover -s tests -p "test_*.py" -v
```

Also parse changed JSON/YAML where practical and verify that relative package paths remain inside `plugins/codex-coordinator/`.

## Accepted product direction

The accepted target is a small, repository-scoped task boundary and visibility layer. The original simplification reasoning is recorded in [the boundary-board review](docs/codebase/2026-07-21_boundary-board-simplification_architectural_review.md); the current reuse-first, cooperative shared-checkout contract and retained protections are recorded in [its accepted correction](docs/codebase/2026-07-23_cooperative-shared-checkout_architectural_review.md).

Until that realignment is implemented and the user explicitly re-enables this repository, keep `.codex/coordination/project.yaml` set to `coordination_enabled: false`.

Future changes must preserve these boundaries:

- Native Codex tasks remain the execution and transcript authority.
- One normal task is the default. Extra durable tasks are for explicit decomposition or independently useful parallel work, not routine commands, checks, or reviews.
- An explicit goal Coordinator reuses a suitable related local task in the same repository and checkout before creating a new local task. One bounded assignment is allowed; polling and acknowledgement loops are not.
- Tasks publish only bounded active ownership metadata. Do not store transcripts, reasoning, prompts, tool output, or full-turn ledgers.
- Keep exact task identity, advisory path-overlap detection, narrow exact exclusive actions, sparse notices, immediate user stop, external-write consent, and evidence-based stale-claim recovery.
- A path or ancestor overlap is a warning, not a task-level stop. Pause only an actual incompatible file hunk, concurrent writer command, or exact exclusive action.
- There is no durable Git owner. Tasks share the established branch, stage and commit only reviewed exact files, preserve foreign staged work, and avoid branch switching, broad staging, history rewrites, or destructive Git cleanup during parallel work.
- Generated maps, lockfiles, schemas, shared indexes, formatter-wide output, and full gates have no durable task owner. Serialize only an actual writer command.
- Do not add a resident Coordinator, persistent heartbeat, all-task reconciliation loop, automatic task-window creation, or mandatory pull-request workflow.
- Mission Control, if retained, is a separately installed, manually started, read-only observer with no task authority.
- Doctor, if retained, is a manual read-only compatibility check. Recovery is normal plugin update or reinstall, not in-place repair or rollback.
- SessionStart must remain bounded and must not launch processes, install Python, scan archives, inspect private Codex databases, or start optional tools.

Treat any proposal that reintroduces orchestration, background monitoring, transcript mirroring, provider or schedule reconciliation, or a second state authority as an architecture change requiring explicit user approval and an update to the decision record.
