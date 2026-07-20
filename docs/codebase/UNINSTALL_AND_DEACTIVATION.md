# Uninstall and deactivation contract

Codex Coordinator has four different lifecycle operations. They must not be collapsed into one
"remove everything" command because they carry different authority and data-loss risks.

## Operations

| Operation | Coordinator package | Project marker | Local project history | Repository heartbeat | Mission Control data |
|---|---|---|---|---|---|
| Pause management | Keep | Keep enabled | Keep | Keep | Keep |
| Deactivate one project | Keep | Set `coordination_enabled: false` | Keep | Remove only that project's Coordinator heartbeat | Keep |
| Uninstall globally | Remove after project deactivation | Keep disabled | Keep | Remove only verified Coordinator-owned repository heartbeats | Stop runtime; keep settings and receipts |
| Purge one project | Keep or remove separately | Remove | Remove | Remove verified project heartbeat | Keep unless separately purged |
| Purge global data | Already uninstalled | Preserve project data unless separately purged | Preserve unless separately purged | Remove only verified Coordinator-owned heartbeats | Remove exact Coordinator lifecycle data |

Normal deactivation and uninstall are reversible. Purge is a separate destructive action that
requires the user to name the project or global data boundary explicitly.

## Project deactivation

Deactivation proceeds in this order:

1. Validate the Git root, schema-1 marker, project ID, primary worktree, and current Coordinator.
2. Reconcile active tasks. Safely finish them or put the repository in report-only mode; never
   discard work merely to deactivate.
3. Produce a dry-run receipt listing every file and native Codex action that would change.
4. Remove exactly the repository heartbeat targeting the registered Coordinator, then archive and
   unpin that Coordinator task when its work has reached a safe boundary.
5. Change only the marker value from `true` to `false` and remove only the exact current Coordinator
   discovery block or an explicitly allowlisted exact legacy version from the root `AGENTS.md`.
6. Preserve `.codex/coordination/`, its marker, task history, inbox, `.gitignore` rules, project
   configuration, Codex tasks, transcripts, and application files.
7. Validate that the marker is disabled and unrelated bytes are unchanged.

Reactivation reverses only the marker and discovery-block changes, normalizes an allowlisted legacy
block to the current packaged block, reloads the installed skill, reconciles the preserved state, and
creates or recovers one pinned Coordinator plus its heartbeat. An arbitrary lookalike block fails
before mutation.

## Global uninstall

Global uninstall never scans an entire drive. It uses an explicit project list and/or a small local
index of previously enabled repositories. The index is non-authoritative: every entry must be
resolved to a Git root and verified against its own marker before use.

For each validated project, perform project deactivation independently. One failed project does not
permit guessing about the others. After all intended projects are safely disabled:

1. Stop Mission Control and persist automatic startup as disabled.
2. Delete only heartbeat automations whose target and prompt prove they belong to a validated
   repository Coordinator. Similar names are not evidence.
3. Remove the plugin with `codex plugin remove codex-coordinator@codex-coordinator`.
4. Remove the Codex Coordinator marketplace only when the user requests it.
5. Remove exact verified legacy skill/hook copies only when they coexist with the plugin and the
   user includes that migration cleanup.
6. Preserve project history and Mission Control settings/receipts by default.

The filesystem helper may prepare and apply exact project-file changes, but native task lifecycle,
automation deletion, Mission Control shutdown, and plugin removal remain explicit Codex/CLI actions.
The helper reports those required actions rather than pretending a local Python process can prove
them.

## Purge

Project purge requires the exact project ID as confirmation. It may remove the verified project
coordination directory, exact discovery block, and exact two-line Coordinator ignore block. It
must not remove the root `.codex` directory, Codex configuration, application files, sessions,
transcripts, databases, worktrees, branches, or unrelated ignore/instruction text.

Global-data purge is a separate explicit action for the exact Coordinator application-data
directory after the plugin is stopped. It never implies project purge.

## Failure and retry behavior

- Dry-run is the default; mutation requires `--apply`.
- Every target is resolved and checked before its first write.
- Multi-file reversible edits are written atomically with rollback on failure.
- Already-disabled or already-removed exact blocks are successful no-ops.
- A changed, malformed, unsupported, linked-worktree, or mismatched target stops before mutation.
- Native actions are recorded as still required until their receipts are verified.
- Repeating the operation after interruption must safely finish or report the remaining exact step.

## Isolated proof

Automated tests use temporary Git repositories and temporary Codex homes. They cover dry-run,
apply, rerun, reactivation, interruption rollback, exact-block preservation, malformed markers,
project-ID confirmation, non-authoritative index validation, and byte-for-byte preservation of
unrelated files and automations. Native task, automation, Mission Control, and plugin commands are
mocked.

A real end-to-end proof belongs in Windows Sandbox or another disposable VM:

1. install the marketplace and plugin;
2. enable two temporary repositories;
3. deactivate one and reactivate it;
4. globally uninstall while preserving both projects' history;
5. reinstall and prove state recovery;
6. run an explicitly approved purge only against a disposable repository.

The development machine's current Coordinator installation is never the test target.
