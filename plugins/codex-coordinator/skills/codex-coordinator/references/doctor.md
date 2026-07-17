# Coordinator Doctor

Read this file completely only for a user-authorised or scheduled check of the installed Coordinator implementation and enabled Coordinator projects. Also read [maintenance.md](maintenance.md) before repairing installed behavior and [recovery.md](recovery.md) before diagnosing stale or inconsistent live state.

Doctor is a bounded maintenance audit, not a second Coordinator. It uses Codex's native project and task inventory, Git, and each project's existing coordination documents. It never creates a service, scheduler, database, dashboard, lock manager, or parallel source of truth. A Codex automation may invoke Doctor on a schedule; the automation remains the scheduler.

## Installed implementation repair

Doctor checks and repairs the implementation that Codex actually loads: the configured global Coordinator skill and exact SessionStart hook. An automatic update is allowed only when the user has configured one exact trusted Codex Coordinator source package and those exact installation targets. Doctor does not discover an arbitrary source directory or treat the source repository as the runtime under diagnosis.

1. Resolve the configured installation targets and verify only the update package identity, manifest, packaged capability contract, skill, deterministic state helper, hook registration, and SessionStart payload needed to make the update safe. Repository tests, release audits, Mission Control checks, and codebase review remain developer or release work outside Doctor.
2. Run `scripts/codex_coordinator_doctor.py --apply` once. It compares the installed files with the trusted package, atomically repairs missing or drifted files, preserves unexpected files, and rolls back the entire attempted update if installation verification fails.
3. Verify the installed implementation itself: exact managed-file hashes, capability-contract version and required behavior markers, durable-complex-only worker creation, parent-owned microtask execution, the one-to-three normal worker target and five-worker ceiling, direct first-turn assignment, control-first Coordinator role, direct-request archived-owner recovery without a repeat-confirmation phrase, the end-of-turn continuation gate and temporary-heartbeat monitoring, inherited model plus cost-safe `low`/`medium` reasoning defaults, native task-lifecycle guidance, deterministic state-helper syntax, Coordinator skill frontmatter, every internal skill link, hook syntax, and a bounded isolated hook smoke run. Then repeat the helper with `--check` to prove the installed implementation is current and healthy.
4. Refresh only the configured global skill directory and exact SessionStart script. Never hand-edit or rewrite a managed plugin cache, marketplace registration, Codex configuration, project file, environment file, or application file.
5. Treat a missing, stale, incomplete, or self-contradictory capability contract as a failed installed implementation even when hashes, frontmatter, links, and hook syntax pass. If package identity, copying, installed-runtime validation, or the final check fails, keep or restore the last working installation where possible and report the exact defect. Do not fall back to partial hand edits.

When the user asks for a visual diagnostic, add `--mermaid-out <private-path>.mmd`. Doctor writes an atomic Mermaid projection of the same JSON result, showing managed-file drift, missing files, repairs, and completed installation checks without embedding machine-specific source or installation paths. The diagram is evidence navigation, not a validator: JSON, exit status, hashes, syntax checks, and the hook smoke run remain authoritative. Do not publish the diagram or write it into an enabled project's coordination state.

Mission Control runs the deterministic installed implementation repair and check directly. It may use one ephemeral model pass only for project findings that require native-task or heartbeat interpretation. That pass receives only enabled project roots and non-terminal task summaries, uses cost-safe medium reasoning, never reloads the full Coordinator skill, and never tests Mission Control or application code.

When Codex exposes a supported update operation for a marketplace-managed installation, use that operation rather than copying into its cache. If no supported updater is available, report the managed installation defect instead of editing its cache. Doctor must not leave a manual and packaged Coordinator installation active together.

## Project discovery

Use an unfiltered native project and task inventory. Resolve the Git common repository and primary worktree for every distinct local task root, then inspect only roots whose primary-worktree `.codex/coordination/project.yaml` has `coordination_enabled: true`. Deduplicate linked worktrees by Git common repository. An explicit configured project root may be added to this inventory, but a task title, filtered search result, or folder name is not project identity.

For each enabled project, read only the marker, `CURRENT.md`, relevant task headers and history, unprocessed inbox records, and the minimum native task status and recent turns needed to test a finding. Do not read application files merely to produce a health heartbeat.

If the affected Coordinator or owner is in an active native turn, defer any check whose evidence could be a normal in-turn transition. Do not report a transient difference between native activity and the last safe canonical boundary. Checks that are independent of that turn, such as malformed immutable identity or an already-proven ownership collision, may still be reported without interrupting the turn.

## Evidence-backed checks

Report only a concrete mismatch that the project Coordinator can verify. Check for:

- malformed or mismatched marker, project identity, epoch, primary-worktree path, canonical tables, or hook recovery state;
- zero, duplicate, foreign, or non-accepting active Coordinator identities where canonical state requires one;
- active ownership that disagrees with task contracts, native task identity, terminal acceptance, released ownership, or pending transitions;
- accepting terminal sessions, acknowledged commands that remain pending, overlapping exclusive ownership, or a task recorded under an unrelated thread goal;
- four or five non-terminal project-execution workers without a recorded per-lane reason showing why each substantial durable lane shortens the critical path, or more than five workers unless canonical task history records a direct user run-wide override;
- a newly recorded durable worker whose contract describes only a routine command, narrow lookup or inspection, mechanical adjustment, or low-risk one-or-two-file fix that should have stayed with the current owner or a parent-owned subagent;
- an unprocessed `TURN_RECONCILIATION` or other inbox record that still lacks a disposition after a later material Coordinator turn;
- a worker whose native completed turn proves terminal completion or a blocker, while its canonical task remains active after a later Coordinator reconciliation;
- queued, blocked, paused, or discovered dependent work that the canonical Resume Queue or task history no longer represents.
- an unattended return path: the exact Coordinator has completed its latest turn, canonical or durable records prove non-terminal work remains, and no enabled Coordinator-owned heartbeat targets it. Verify the heartbeat absence from the current native automation inventory or configured local automation definitions; do not infer it from task status or age. Use issue code `UNATTENDED_RETURN_PATH` and include whether the single result/blocker fallback is actually available.

Time, `idle`, or `notLoaded` alone never proves that a task is abandoned, forgotten, stale, or unusable. A report that arrived while the Coordinator was running is not unattended unless a later Coordinator reconciliation boundary passed without disposition. The `UNATTENDED_RETURN_PATH` check is different: it requires a completed Coordinator turn, proven non-terminal project work, and verified absence of the required heartbeat. Do not wake a task to ask what it is doing; use native status, recent turns, project records, and native automation evidence.

## Doctor findings

Doctor may write one unique append-only record to the affected primary worktree's `.codex/coordination/inbox/` only when a verified mismatch exists. It never edits `CURRENT.md`, task files, task history, ownership, the Resume Queue, `AGENTS.md`, `.gitignore`, project configuration, Git state, or application files. It sends no cross-task message, creates no task, and wakes, pauses, resumes, stops, or archives no task.

Use a create-if-absent filename containing the timestamp, `doctor`, and finding ID. Begin with:

```yaml
type: DOCTOR_FINDING
project_id:
coordination_epoch: <current epoch or UNKNOWN when malformed state is the finding>
finding_id:
fingerprint:
reported_by: CODEX_COORDINATOR_DOCTOR
state: REVIEW_NEEDED
severity: LOW | MEDIUM | HIGH
detected_at:
```

Then record the issue code, minimal evidence, affected task or thread identities, canonical state versus native state, safe work that may continue, recommended Coordinator disposition, and whether a real user decision is likely required. Do not copy transcript bodies, secrets, credentials, or unrelated project content.

Build `fingerprint` deterministically from project ID, issue code, affected identities, and normalized mismatch facts. Before writing, scan unresolved `DOCTOR_FINDING` records in that project's inbox. If the same fingerprint already exists, do not create another record. Do not edit, resolve, rename, or delete an existing finding.

## Coordinator disposition

At the start and end of a coordinating turn, the project Coordinator processes `DOCTOR_FINDING` with the other inbox records. It validates the finding against current native status and canonical state. It records stale, duplicate, or already-fixed findings as rejected or satisfied; otherwise it repairs canonical coordination state within its normal authority, assigns or queues authorised work, or asks the user for a genuine missing decision. Doctor's recommendation is never authority or permission.

Finish the scheduled run with one quiet summary: installed implementation repair status, enabled projects checked, new findings by severity, and projects needing Coordinator review. Do not send per-project status messages or wake Coordinators merely to announce a finding; the durable inbox is the handoff.
