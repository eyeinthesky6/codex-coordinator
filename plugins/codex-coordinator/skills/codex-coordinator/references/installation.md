# Installation and project enablement

Read this file completely only when the user asks to install, enable, disable, or initialise Codex Coordinator.

## Boundaries

- The plugin installs one global skill and one small read-only SessionStart hook.
- Python 3.10 or newer must already be available. Installation never installs Python, changes PATH, invokes an OS package manager, or asks for administrator access.
- SessionStart reads the bounded project marker and counts only the exact current task's pending-delivery filenames. It reads no record body and launches no child process or optional tool.
- No optional observer, Coordinator task, pin, or heartbeat is started or installed as part of project enablement. A user may later appoint one goal-scoped Coordinator; that exact native task pins itself after taking the goal, leaves unpinning to the user, and may use a temporary native thread heartbeat only when unattended supervision is explicitly requested.
- Project state contains a trackable marker, ignored active claims and cold receipts, plus a generated active-only `CURRENT.md` view after the first claim. A failed native assignment or terminal return may temporarily leave one ignored routing-only record under `pending-notices/`; verified receipt or recipient action deletes it. There is no always-on Coordinator, heartbeat, general inbox, acknowledgement ledger, or task transcript store.

## Enablement preflight

Before writing project files:

1. Resolve the Git root and primary worktree.
2. Inspect the root `AGENTS.md`, root `.gitignore`, marker, Git status, and active native tasks that could own those exact files.
3. Preserve unrelated bytes and existing dirty work.
4. Stop before all writes if the marker or exact insertion cannot be changed safely.

## Marker schema 2

```yaml
schema_version: 2
coordination_enabled: true
project_id: <stable-lowercase-project-id>
project_name: <project-name>
task_prefix: <short-uppercase-prefix>
active_task_ceiling: 5
canonical_paths:
  active: .codex/coordination/active
  archive: .codex/coordination/archive
access:
  cross_project_task_access: false
  cross_project_state_changes: false
```

Keep the marker trackable. Ignore all other coordination state with:

```gitignore
.codex/coordination/*
!.codex/coordination/project.yaml
```

Do not ignore all of `.codex`, the root `AGENTS.md`, or project configuration.

## Root discovery block

Add only this exact block and preserve every unrelated instruction:

```markdown
## Codex task-boundary board

- This repository uses the opt-in Codex task-boundary board in `.codex/coordination/project.yaml`.
- Before substantial writes, load the installed `codex-coordinator` skill, list active claims from the primary worktree, and publish only this task's bounded claim.
- Native Codex tasks remain the goal, continuation, execution, messaging, and transcript authority; durable parallel tasks use native Goal mode, while short work stays in the current task or a parent-owned helper.
- An explicitly requested goal Coordinator supervises exact assigned task events. Only a user-requested unattended goal may use one temporary native thread heartbeat; there is no repository heartbeat or mandatory pull-request workflow.
- Five active durable tasks, including the Coordinator, is the default ceiling. Only a direct user instruction may approve a higher temporary goal count or change `active_task_ceiling`.
- The exact goal Coordinator pins itself after taking the goal. Project enablement never pins tasks, workers are never pinned by Coordinator, and only the user unpins a task.
- Reject cross-project inter-agent task communication and never store transcripts, reasoning, prompts, or tool output in Coordinator state.
```

## Enable

For a new project, first review the no-write plan:

```powershell
python scripts/codex_coordinator_project.py `
  project init --project-root C:\Projects\example `
  --project-id example --project-name "Example" --task-prefix EX
```

Repeat with `--apply` only after the plan is approved. The helper rejects an existing marker or any unmarked coordination state instead of guessing ownership.

1. Create or migrate the marker only under direct user authority or the explicit repository trigger in the main skill.
2. Add the exact ignore and discovery blocks.
3. Do not create a Codex task, `CURRENT.md`, task contract, inbox, heartbeat, observer process, Doctor schedule, or placeholder record.
4. Validate the marker and run the state helper's empty `list` command.
5. Keep the project single-task until each real writer can publish its own exact native claim.

## Change the project ceiling

Five active durable tasks, including the Coordinator, is the default. An older schema-2 marker
without `active_task_ceiling` also means five. A direct user request may set a different persistent
project ceiling. Review the no-write plan first:

```powershell
python scripts/codex_coordinator_project.py `
  project set-ceiling --project-root C:\Projects\example `
  --active-task-ceiling 8
```

Repeat with `--apply` only under that direct approval. The command changes only the marker, preserves
active claims and history, and creates no native task or background action. Lowering the ceiling does
not stop existing tasks; it prevents new unapproved claims until the active count falls below the new
ceiling. For one goal only, keep the marker unchanged and use the exact higher count the user approved.

Schema-1 mutable history is preserved and ignored. Do not infer active schema-2 claims from old task or inbox files.

## Disable

Disabling is reversible and not a purge:

1. Let active writers reach a safe boundary and release or preserve their exact claims.
2. Dry-run the packaged lifecycle helper.
3. Set only `coordination_enabled: false` and remove only the exact discovery block.
4. Preserve the marker, active or archived records, legacy history, native tasks, transcripts, Git history, project config, and application files.

Re-enable only when the marker uses schema 2 and the user explicitly requests it. No background process or task must be restored.
