# Uninstall and deactivation contract

Deactivation, migration, global uninstall, and purge are different operations. The lifecycle helper is dry-run-first and operates only on an explicitly named primary Git worktree.

## Schema-2 deactivation

Deactivation:

- sets only `coordination_enabled: false`;
- removes only the exact packaged discovery block from `AGENTS.md`;
- creates no task, pin, heartbeat, schedule, or Mission Control action;
- preserves the marker, active claims, cold receipts, schema-1 history, native tasks and transcripts, Git history, application files, config, env, ignore rules, and unrelated guidance.

Reactivation is allowed only for schema 2 and only after direct user approval. It restores the exact discovery block and marker flag. It starts nothing.

## Legacy schema 1

Legacy projects may contain a resident Coordinator and heartbeat. Deactivation reports cleanup actions only for that proven old schema and exact recorded Coordinator ID. It never creates a replacement.

Schema 1 cannot be reactivated directly. The dry-run-first migration writes only a disabled schema-2 marker, an exact schema-1 marker backup, and empty `active/` and `archive/` directories. It inventories legacy project state but never converts old task records into live claims. Legacy `CURRENT.md`, tasks, inbox, cache, feedback, and transcripts remain preserved and ignored.

Migration apply requires all of these:

- the schema-1 project was deactivated first, including removal of the exact discovery block;
- `--confirm-project-id` matches the validated marker;
- the user confirms that the old Coordinator heartbeat and any optional Mission Control process are stopped;
- the new board directories are absent or empty.

The helper does not inspect native Codex state or external observer state to manufacture that confirmation.

## Commands

Dry-run deactivation:

```powershell
python plugins/codex-coordinator/scripts/codex_coordinator_uninstall.py `
  project deactivate --project-root C:\Projects\example
```

Apply only after reviewing the plan:

```powershell
python plugins/codex-coordinator/scripts/codex_coordinator_uninstall.py `
  project deactivate --project-root C:\Projects\example --apply
```

Reactivation:

```powershell
python plugins/codex-coordinator/scripts/codex_coordinator_uninstall.py `
  project reactivate --project-root C:\Projects\example
```

Dry-run schema migration:

```powershell
python plugins/codex-coordinator/scripts/codex_coordinator_uninstall.py `
  project migrate --project-root C:\Projects\example
```

Apply only after reviewing the inventory and stopping the legacy runtime:

```powershell
python plugins/codex-coordinator/scripts/codex_coordinator_uninstall.py `
  project migrate --project-root C:\Projects\example `
  --confirm-project-id example `
  --confirm-legacy-runtime-stopped `
  --apply
```

Migration keeps `coordination_enabled: false`. Reactivation remains a later, explicit user action after source/install validation.

## Global uninstall planning

Global planning reads a small local index plus explicitly supplied project roots and revalidates every marker. It never scans a drive. A rejected or ambiguous project does not block safe reporting for verified projects.

For schema 2, there are no native task actions. For schema 1 only, the plan may require stopping a verified old heartbeat and Coordinator task. A separately configured legacy Mission Control auto-start is also legacy cleanup, not part of schema 2.

Plugin removal remains a normal plugin-manager operation after verified projects are disabled.

## Purge

Purge is destructive and separate. It requires:

- the exact primary worktree;
- a validated marker;
- `--confirm-project-id` equal to that marker;
- an explicit `--apply` after dry-run review.

It removes the exact Coordinator discovery and ignore blocks and deletes only that project's `.codex/coordination/` state through a bounded quarantine step. It does not delete native Codex tasks, transcripts, Git history, application files, unrelated automation, config, or env.

## Retry and preservation

Document writes are prepared and rolled back on failure. Purge can resume only from its exact verified quarantine. Duplicate or modified discovery blocks fail instead of broad text deletion. Linked worktrees cannot perform lifecycle mutation.

No operation re-enables a project automatically.
