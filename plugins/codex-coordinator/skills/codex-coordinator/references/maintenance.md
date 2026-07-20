# Coordinator maintenance

Read this file completely only when the user explicitly asks to install, repair, harden, upgrade, or remove Codex Coordinator, or to review a Coordinator-system suggestion. For installation or `AGENTS.md` work, the main routing table also selects the installation lane.

## Maintainer authority

Use `COORDINATOR_MAINTAINER` only under explicit user authority. It manages Coordinator itself and remains `COORDINATOR_SYSTEM / accepts=false`; it never becomes the project Coordinator or recipient for ordinary assignments, findings, acknowledgements, or status.

Coordinator installation or hardening does not authorise application changes, environment edits, global config changes beyond the exact request, or broader project guidance changes.

Before an installation, repair, or Doctor `--apply` writes outside the current repository, give the user one advance notice naming the exact installed skill, hook, configuration, project, or bounded destination and the reason for the write. Codex full-access mode and tool permission do not replace this disclosure or expand scope. When the user's direct request already names and authorises that external target, proceed after the notice without asking for the same approval again. Otherwise wait for explicit approval. A read-only Doctor `--check` needs no write notice.

A user-approved recurring Doctor may reuse the bounded project inbox targets disclosed when the automation was configured. Newly discovered projects or external destinations require a fresh notice and approval before the automation writes there; until then it reports the target as awaiting authorisation and leaves it unchanged.

Apply the main skill's Project enablement trigger and Coordinator creation authority without adding maintenance-specific alternatives. Maintainer authority by itself triggers neither project enablement nor project-task creation.

When an enabled project's canonical state is idle with no active ownership or pending transition, an explicitly user-authorised Maintainer may perform bounded Coordinator-package maintenance without registering as a project-execution worker or changing `CURRENT.md`. First use unfiltered native discovery to confirm there is no overlapping same-repository work. A filtered search miss is not proof. If discovery remains uncertain, preserve state and report the blocker; never ask the user to approve a coordination bypass because approval cannot replace native identity or overlap evidence.

## Protected files

Only a user-authorised Maintainer may change:

- the global Codex Coordinator skill package;
- the bundled Mission Control companion files and lifecycle helper;
- the Coordinator block in repository `AGENTS.md`, or an exact legacy global block during migration or removal;
- `.codex/coordination/project.yaml`;
- the plugin-managed hook registration and SessionStart script, or an exact legacy global hook entry during migration or removal;
- the exact Coordinator-state block in a project root `.gitignore`.

Only the active project Coordinator changes `CURRENT.md` and project-execution task files. A registered worker writes one unique append-only `.codex/coordination/inbox/` `TURN_RECONCILIATION` record at the end of each material turn and may create the other narrowly allowed records under the operations lane. A scheduled or user-authorised Doctor may create only a deduplicated append-only `DOCTOR_FINDING` under the Doctor lane. These exceptions grant no canonical-state edit or ownership authority. A Maintainer may update `CURRENT.md` and its own maintenance task only to register or reconcile maintenance, including required pause and resume transitions.

Legacy project-local Coordinator READMEs, manuals, skill or hook copies, and `system-source` files are non-authoritative. Do not read or synchronize them. Remove them only under explicit user authority for that repository.

Adding the Coordinator-state block to `.gitignore` does not untrack existing files. Removing mutable state paths from the Git index is allowed only when the user explicitly asks to stop tracking Coordinator state and the active Git integration owner has confirmed a safe boundary. Keep the working files and keep `project.yaml` trackable; do not remove project coordination state from disk.

After a global skill or hook change, require resumed coordinated sessions to reload the global skill before acting. Threads retain previously loaded instructions until reloaded. After a Mission Control package change, restart a running Mission Control process so it serves the current source bytes; verify that restart through Mission Control's own health check and UAT rather than Doctor.

Keep maintenance reports user-facing and plain. Do not expose epochs, task or thread IDs, scope kinds, acceptance flags, or role constants unless the user explicitly asks for raw diagnostics.

## Deactivation, uninstall, and purge

Keep four operations separate:

- a user pause changes an enabled repository to report-only monitoring and removes nothing;
- project deactivation is reversible and preserves local coordination history;
- global uninstall deactivates verified known projects, stops Coordinator-owned lifecycle components, and removes the plugin while preserving project history;
- purge is a separate destructive request for exact project or application-data state.

Use `scripts/codex_coordinator_uninstall.py` from the trusted installed plugin. Every filesystem operation is dry-run-first; mutation requires `--apply`. The helper validates the primary Git worktree, schema-1 marker, project ID, and exact current or explicitly allowlisted legacy instruction block plus the exact ignore block before writing. Reactivation replaces an allowlisted legacy discovery block with the current packaged block. Arbitrary lookalikes fail before mutation. The helper never scans an entire drive and never runs Codex task, automation, Mission Control, or plugin commands implicitly.

For one project:

1. Reconcile active work to a safe boundary without discarding or stashing user changes.
2. Run `project deactivate --project-root <primary-worktree>` and inspect every planned file and native action.
3. Remove only the verified repository heartbeat, then archive and unpin the exact registered Coordinator at its safe boundary.
4. Run the same command with `--apply`; validate the disabled marker, removed exact discovery block, and preserved history.

For global uninstall:

1. Build or update the bounded local index only from explicitly known repositories with `index-project --project-root <primary-worktree> --codex-home <codex-home> --apply`. This external application-data write requires the advance disclosure above. The index is non-authoritative.
2. Run `global-plan --codex-home <codex-home>` and revalidate every candidate against its live Git root and marker. Extra `--project-root` values may be supplied explicitly. Reject stale paths and project-ID mismatches; never replace this with a drive scan.
3. Deactivate each verified enabled project independently through the one-project procedure. One failure does not authorise guessing about another project.
4. Run the packaged Mission Control lifecycle stop command so automatic startup remains disabled.
5. Remove only heartbeat automations whose exact target and prompt prove that they belong to those verified repository Coordinators. Similar names are not evidence.
6. Remove the plugin with `codex plugin remove codex-coordinator@codex-coordinator`. Remove its marketplace or exact verified legacy skill/hook copies only when the direct request includes them.
7. Verify project histories, Mission Control settings and receipts, unrelated automations, Codex sessions and transcripts, global configuration, application files, and environment are unchanged.

Project purge uses `project purge --project-root <primary-worktree> --confirm-project-id <exact-id>` and remains a dry run until `--apply`. It may quarantine and remove only the verified `.codex/coordination/` directory plus the exact packaged discovery and ignore blocks. Never remove the root `.codex` directory, `.codex/config.toml`, Codex sessions or databases, application code, Git worktrees or branches, or unrelated instructions and ignore entries. Global Coordinator application-data purge is another separate direct request after the plugin and runtime are stopped.

Test this lifecycle with temporary Git repositories, a temporary Codex home, mocked native actions, interruption injection, and a disposable sandbox or VM for real install-to-uninstall proof. Never deactivate or uninstall the working machine merely to validate source changes.

## Reinstall boundaries

A normal plugin reinstall may replace only the plugin-managed global package or cache. It must not rewrite project `AGENTS.md`, `.gitignore`, `.codex/config.toml`, markers, current state, task records, inbox records, suggestions, application files, or environment files. Preserve both enabled and explicitly opted-out projects. A separate user-authorised project repair or schema migration is required for any project-file change.

When moving a machine from a manual global installation to the packaged plugin, do not leave both copies active. Install the plugin, verify its skill and hook in a new task, then remove only the legacy manual Coordinator skill copy and exact legacy hook entry and script. Preserve unrelated global instructions and every project file.

## Upgrade a working project

Classify the upgrade before changing anything:

- **Behavior-only:** update the global skill once. Do not edit project files. In-flight turns may reach their existing safe boundary; before their next coordinated action, affected agents reload the skill from disk and the project Coordinator reconciles state. The next coordinated turn and SessionStart recovery require this reload without user cleanup.
- **Hook-only:** update the global hook once. It applies on the next SessionStart. Running agents continue from canonical state and reload the skill at their next safe boundary.
- **Project-schema or discovery change:** update the global skill first, then migrate each enabled repository separately under explicit Maintainer authority. Use the existing marker `schema_version` as the compatibility check; do not add a project-local behavior version or copy global guidance into the repository.

For an active project-schema migration:

1. Let in-flight agents reach a safe turn boundary. Pause only coordination transitions and work whose ownership interpretation depends on the changed schema; do not freeze unrelated safe work.
2. Preserve the project ID, current ownership, task contracts, pending transitions, and working files. Never reinstall, reset state, or copy another project's files.
3. Migrate only the Coordinator marker, state shape, discovery block, ignore block, or hook integration required by the new schema.
4. Validate the marker version and identity, parse current state, verify discovery and ignore rules, and confirm no application or unrelated project file changed.
5. Require affected agents to reload the global skill, reconcile pending state, then resume the paused work. The user performs no manual migration or thread cleanup.

If compatibility or validation fails, stop new coordination transitions, preserve the existing project state and authorised work, and report the exact migration blocker. Do not partially guess a schema conversion.

## Project AGENTS.md boundary

During installation, repair, hardening, or removal, edit project-level `AGENTS.md` only to add, repair, or remove the exact minimal Coordinator discovery block supplied by the installation lane.

Do not:

- place SOPs, message formats, task protocols, state, coding rules, architecture rules, testing rules, or unrelated Git policy in `AGENTS.md`;
- rewrite, reorganize, shorten, expand, or deduplicate unrelated instructions;
- create or modify nested `AGENTS.md`, `AGENTS.override.md`, or other nested instruction files;
- turn a project finding, unclear convention, or agent mistake into an instruction edit.

Treat every project `AGENTS.md` as read-only during ordinary Coordinator use.

A non-Coordinator instruction change is allowed only when the codebase genuinely needs a persistent instruction, the change is separate from Coordinator operation, the user separately and explicitly requests it, and an authorised agent receives a bounded task for it. Keep it separate from the Coordinator block and preserve the instruction hierarchy.

After any edit, show the exact Coordinator block, verify unrelated text is unchanged, report whether any non-Coordinator line changed and why, and revert incidental changes.

## Coordinator-system suggestions

Use `.codex/coordination/suggestions/` only for defects or improvements in Codex Coordinator itself. Valid types are:

- `COORDINATOR_IMPROVEMENT`;
- `COORDINATOR_BUG`;
- `COORDINATOR_INCOMPLETE_FLOW`;
- `COORDINATOR_CAPABILITY_GAP`;
- `COORDINATOR_DISCOVERY_FAILURE`;
- `COORDINATOR_SAFETY_CONCERN`.

A task agent, adviser, or reviewer may create one new suggestion file after observing a Coordinator-system problem. It may not modify, rename, resolve, delete, or implement an existing suggestion, or change Coordinator internals. Only a user-authorised Maintainer may act on it.

Start every suggestion with:

```yaml
type:
project_id:
related_task_id:
reported_by:
severity:
status: OPEN
```

Then include:

- Observed Coordinator-system problem
- Evidence
- Expected behavior
- Workaround used
- Suggested improvement
- Possible downside or risk

Keep evidence generic. Do not copy foreign project paths, task or thread IDs, transcripts, or state into another project's coordination tree.

Application bugs, missing tests, architecture concerns, dependencies, refactors, project documentation, and feature ideas are project findings. Report them through the active Coordinator; never put them in suggestions.

## Pause, reload, and resume

When maintenance affects active project work:

1. Record mode `MAINTENANCE` and mark affected tasks `PAUSED`.
2. Record the reason, exact resume condition, and authorised resumer.
3. Deliver `PAUSE` under the safe-message policy and record acknowledgement.
4. Make global-skill reload part of the resume condition when the skill or hook changed.
5. Before finishing, restore the previous mode and send `RESUME`, or leave an explicit pending entry in the Resume Queue for the project Coordinator.

Never finish maintenance with silently paused work. Do not resume work that conflicts with current user instructions. The Maintainer may issue only recorded maintenance `PAUSE`, `STOP`, `RESUME`, and boundary-correction transitions. It remains outside project-execution ownership and may not send application, Git, deployment, database, environment, or other project-execution commands.
