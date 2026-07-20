# Installation and onboarding

Read this file completely only when the user asks to install, enable, initialise, repair discovery, demonstrate, or explain initial use of Codex Coordinator.

## Installation authority and boundaries

Apply the main skill's **Project enablement trigger** exactly; this lane does not add another trigger. When it selects enablement, that selection grants bounded `COORDINATOR_MAINTAINER` authority over Coordinator files and the exact Coordinator-state block in the root `.gitignore`, plus the main skill's bounded authority to create, pin, and register exactly one repository Coordinator. Project `.codex/config.toml` remains read-only unless the user separately and explicitly asks to set a project model or reasoning default. Do not touch application code, environment files, unrelated configuration, or unrelated instructions.

Keep global behavior separate from project state:

- The global skill contains Coordinator behavior.
- The global read-only SessionStart hook provides restart context.
- The bundled Mission Control companion observes local native and Coordinator records and exposes the bounded Doctor action; it is not project state or a second authority.
- Project files contain identity and current state only.

The installed plugin exposes the global skill to agents. An enabled repository's minimal root `AGENTS.md` block provides project-local discovery; no global `AGENTS.md` edit is required for a clean plugin install.

## Python runtime bootstrap

The SessionStart registration first runs the packaged OS-native bootstrap. It accepts only Python 3.10 or newer and checks PATH, the Windows Python launcher and registry where applicable, standard installation folders, and bounded Codex runtime-cache folders. It validates every candidate before using it. Do not recursively scan an entire drive, another user's profile, or unrelated directories.

If no compatible interpreter exists, the bootstrap writes a plain notice before attempting installation. Prefer an existing user-scoped installer: `winget --scope user` on Windows, then `uv` or Homebrew on supported Unix systems. A system package manager may run only when the current process is already root. Never invoke `sudo`, prompt for an administrator password, permanently edit PATH, or download an unverified standalone binary. If installation is unavailable or fails, return valid SessionStart output explaining that Python 3.10+ is required so the task can continue without a broken hook response.

Once selected, the same interpreter runs the Coordinator hook and its bundled Mission Control lifecycle. A discovered Codex-bundled interpreter is a best-effort fallback; do not hardcode one versioned cache path or describe that internal path as a stable Codex API.

## Mission Control lifecycle

The first valid SessionStart in any enabled Coordinator repository starts or reuses the bundled localhost Mission Control server. It opens the dashboard only on that first automatic launch. Later sessions reuse the process without opening duplicate tabs.

When Coordinator enables a previously unmarked repository during the current task, SessionStart has already passed. After the marker and initial state validate, make the bounded local application-data disclosure required below, then run `scripts/mission_control_lifecycle.py start --automatic --project <primary-worktree>` once. This gives first-time enablement the same behavior without requiring another Codex task or restart.

Mission Control keeps `automatic_start_enabled` and whether the first browser launch occurred in its existing local application-data directory. It never writes that preference into a project, plugin cache, global config, or environment file.

When the user asks in chat to **Start Mission Control**, disclose that the action writes the lifecycle preference in the operating system's local Codex Coordinator application-data directory and starts a localhost process, then run the packaged `scripts/mission_control_lifecycle.py start --project <primary-worktree> --open`. This explicit request authorises that bounded preference write and process start. Report the returned status and URL.

When the user asks in chat to **Stop Mission Control**, make the same bounded application-data disclosure, then run `scripts/mission_control_lifecycle.py stop`. This disables automatic restart and requests a graceful server shutdown. A stop request while no server is running still records the disabled preference. **Start Mission Control** explicitly re-enables it.

For a read-only status request, run `scripts/mission_control_lifecycle.py status`. Do not edit environment or Codex configuration for any lifecycle command. If the packaged runtime is missing, report the installation defect instead of downloading code or guessing a source checkout.

Never copy or synchronize a Coordinator README, capability manual, skill, hook, `system-source`, SOP, template library, or behavior summary into a project. Existing project-local copies are non-authoritative. Remove them only when the user explicitly authorises removal in that repository.

## Project files

Coordinator-specific project content is limited to:

- the minimal Coordinator block in the root `AGENTS.md`;
- the exact Coordinator-state entries in the root `.gitignore`;
- `.codex/coordination/project.yaml` for stable identity and canonical paths;
- `.codex/coordination/CURRENT.md` for changing state;
- `tasks/` when a real task exists;
- `inbox/` when a real durable handoff record exists;
- `suggestions/` when a real Coordinator-system report exists.

The installer preserves `.codex/config.toml` by default. Coordinator-generated tasks inherit the user's configured model while the global operating contract explicitly uses `low` or `medium` reasoning unless managed policy or an explicit per-task or run-wide user override applies. Under a separate explicit request, the installer may minimally merge an exact project model or reasoning default; this remains ordinary Codex configuration, not Coordinator state or a synchronization target.

Keep `project.yaml` trackable because it is the repository discovery marker. Treat every other `.codex/coordination/` path as local operational state. Add this exact root `.gitignore` block before creating Coordinator state:

```gitignore
.codex/coordination/*
!.codex/coordination/project.yaml
```

Do not ignore the root `AGENTS.md`, `.codex/config.toml`, or all of `.codex/`. Preserve every unrelated `.gitignore` line and comment exactly.

Keep `project.yaml` stable. Put epoch, mode, Coordinator, sessions, tasks, ownership, pending commands, and other changing fields only in `CURRENT.md` or task files.

## Bootstrap preflight

Before the first project-file write, finish one read-only preflight across the whole bootstrap set:

1. Resolve the primary worktree and Git common repository; never bootstrap canonical state in a linked worktree.
2. Inspect Git status and the existing contents or absence of the root `AGENTS.md`, root `.gitignore`, `.codex/config.toml`, and `.codex/coordination/` marker and state. Preserve unrelated bytes and existing dirty work.
3. Use native task discovery to identify other currently active tasks in that same Git common repository and inspect whether any owns or is changing one of those exact paths. If overlap exists, or a safe boundary cannot be established, stop with `BOOTSTRAP_COLLISION`, make no partial Coordinator edits, and report the exact path and owner uncertainty.
4. Verify that existing marker and config files parse and that every planned insertion is a narrow merge. If any target cannot be preserved safely, stop before all writes.

An active same-repository task with proven disjoint ownership is not itself a blocker. Bootstrap changes never grant permission to stage, commit, reset, restore, stash, clean, or otherwise alter its work.

## Enablement procedure

Run this procedure only when the main skill's Project enablement trigger selects enablement. Otherwise create no project files.

1. Confirm the target is a Git repository and resolve its root.
2. Complete the Bootstrap preflight above.
3. If an existing marker is explicitly opted out and the main trigger does not authorise re-enable, make no changes. When re-enabling, preserve existing identity and state. If it is enabled, do not reinstall, reset the epoch, erase tasks, or replace state; use the missing-state procedure below if only `CURRENT.md` is absent.
4. Use the user-provided project ID. Otherwise use the normalized root directory name only when unambiguous. Keep it stable.
5. Add only the exact discovery block below to the root `AGENTS.md`. Never create or change nested instruction files.
6. Add the exact two-line Coordinator-state block to the root `.gitignore` if absent. When `.gitignore` is absent, create it with only that block.
7. Check whether any mutable `.codex/coordination/` paths are already tracked. An ignore rule does not affect tracked files. Do not alter the Git index unless the user explicitly asked to stop tracking Coordinator state; when authorised, first verify the active Git integration owner, then remove only the mutable state paths from the index while keeping their working files. Keep `project.yaml` trackable.
8. In a new unmarked repository, create fresh `project.yaml` and `CURRENT.md` only. Never copy IDs, epochs, tasks, sessions, or state from another repository.
9. Reuse the global skill and SessionStart hook. Do not create project-local Coordinator behavior files.
10. Preserve `.codex/config.toml` byte-for-byte and create no project model default unless the user separately asks for one. Native Coordinator task creation inherits the user's configured model while explicitly using the cost-safe `low` or `medium` reasoning policy.
11. When the user explicitly requests a project default, resolve the exact supported model/reasoning combination from the target host, confirm any unavailable exact choice, then create or minimally merge only `model` and `model_reasoning_effort`. Preserve every unrelated setting and never edit global config.
12. Initialise `CURRENT.md` as a short `ATTENTION_NEEDED` bootstrap transition with shared goal `none`, Coordinator `NONE / UNREGISTERED / accepts=false`, and empty required tables including `Excluded tasks`.
13. Apply the main skill's Coordinator creation authority immediately: create one complete native Coordinator task, bind its exact identity, pin it, register it as `IDLE / accepts=true`, switch mode to `MANAGING`, and verify one repository heartbeat. Do not claim enablement complete until all of these receipts exist.
14. Create `tasks/`, `inbox/`, or `suggestions/` only when writing the first real record of that kind. Do not add placeholders.
15. After the enabled marker and registered state pass validation, run the packaged Mission Control lifecycle helper in automatic mode as described above. Re-enabling a repository must respect an existing user-disabled Mission Control preference; automatic mode never overrides it.

## Enabled marker with missing local state

An enabled marker without canonical `CURRENT.md` is possible local-state loss, not a normal reinstall.

1. Verify the supported marker and derive the expected project ID from that primary-worktree marker.
2. Use native discovery to prove that no other task besides this authorised bootstrap task is currently active in the same Git common repository. A timeout, unavailable tool, incomplete listing, uncertain repository match, or any other active same-repository task fails this proof.
3. Complete the Bootstrap preflight for the missing state path and inspect surviving local task records without deleting or rewriting them.
4. Only after that proof, recreate `CURRENT.md` in the exact compact shape from the main skill with mode `ATTENTION_NEEDED`, no active shared goal, an unregistered non-accepting Coordinator, and empty tables including `Excluded tasks`. Preserve the marker, project ID, surviving task records, project config, and all unrelated files.
5. Create or recover and pin the repository Coordinator, then switch to `MANAGING`, restore `IDLE / accepts=true`, and verify the repository heartbeat before substantial project work.

If the proof fails, report `LOCAL_COORDINATION_STATE_MISSING`, make no Coordinator-state change, send no project message, and do not begin substantial overlapping writes. Never infer that missing ignored state is safe merely because the tracked marker survived a clone or checkout.

## Marker

Use this minimum shape without project-specific policy:

```yaml
schema_version: 1
coordination_enabled: true
project_id: <stable-lowercase-project-id>
project_name: <project-name>
task_prefix: <short-uppercase-prefix>
canonical_paths:
  current: .codex/coordination/CURRENT.md
  tasks: .codex/coordination/tasks
  suggestions: .codex/coordination/suggestions
access:
  cross_project_task_access: false
  cross_project_state_changes: false
```

Treat `true` as enabled and `false` as an explicit project opt-out. Marker absence means not yet initialised, not opted out. On an explicit opt-out, set the existing marker to `false`, remove only the exact Coordinator discovery block from the root `AGENTS.md`, and preserve identity, state, tasks, ignore rules, and project config. On re-enable, set it to `true`, restore the exact discovery block, reload the global skill, and reconcile existing state without resetting it.

## Root AGENTS.md discovery block

Use this exact block:

```markdown
## Codex Coordinator

- This repository is Codex Coordinator-enabled.
- Project identity is in `.codex/coordination/project.yaml`; current coordination state is in `.codex/coordination/CURRENT.md`.
- Load the globally installed `codex-coordinator` skill at the start of every task in this repository; all same-repository tasks are managed by default unless the user explicitly excludes one.
- Respect the project ID and assigned task boundary; reject missing or mismatched cross-thread project bindings.
- Treat Coordinator internals as protected; only an explicitly user-authorised `COORDINATOR_MAINTAINER` may modify them.
```

Preserve every non-Coordinator line exactly. Do not reorganize, shorten, expand, deduplicate, or improve unrelated guidance.

## First-run demonstration

Demonstrate discovery without creating fake project work:

1. Re-read the marker and `CURRENT.md` as a new thread would.
2. Show that the pinned Coordinator sees a small isolated task without creating unnecessary worker processes.
3. Explain that every task is managed by default and real parallel work records clear ownership before assignments begin.
4. Confirm that a system-maintenance agent repairs Coordinator only and never receives ordinary project work.
5. Do not create fake workers, acknowledgements, or messages. The one pinned Coordinator created by enablement is the real lifecycle task, not demonstration data.

## User handoff

Report:

- the project name, marker path, state path, and whether Coordinator is ready or currently coordinating work;
- whether the model will inherit the user's configured default, whether generated tasks will use cost-safe `low` or `medium` reasoning, and whether the user requested an exact override;
- whether `.gitignore` changed and whether `.codex/config.toml` was preserved or explicitly amended;
- whether any pre-existing Coordinator paths were already tracked or explicitly removed from the index;
- exact files changed and validation results;
- the harmless first-run demonstration.

Do not expose epochs, task IDs, thread IDs, role constants, scope kinds, acceptance flags, or mode constants in the normal handoff. Provide raw values only when the user asks for diagnostics.

Explain simply: the global plugin is discoverable everywhere but manages nothing until a repository is enabled; an enabled repository keeps one pinned Coordinator; all its tasks are managed by default; only the user can exclude a task or pause management into report-only mode; documents hold authority; and messages only deliver recorded state.

Give these example prompts:

```text
Use $codex-coordinator to create the tasks needed and coordinate this goal: <goal>

Use $codex-coordinator to report who is working on what, what is waiting, and what is blocked without changing anything.

Use $codex-coordinator to repair only the Coordinator system.

Start Mission Control.

Stop Mission Control.

Turn Codex Coordinator off for this repository.
```

## Validation

Verify all of the following:

- marker and state project IDs match;
- `coordination_enabled` is `true` after enablement or `false` only for an explicit opt-out;
- access flags are false;
- bootstrap target paths passed the collision preflight before the first write;
- `CURRENT.md` has each exact required field, heading, and table header once;
- missing local state was recreated only after native discovery proved no other active same-repository task;
- changing operational fields appear only in `CURRENT.md` or task files;
- the root discovery block occurs once and matches exactly;
- unrelated `AGENTS.md` content is byte-for-byte preserved;
- no nested instruction file changed;
- no duplicate project-local Coordinator guidance exists;
- `.codex/coordination/project.yaml` is not ignored;
- `CURRENT.md`, task records, suggestions, and other mutable `.codex/coordination/` contents are ignored;
- no mutable `.codex/coordination/` path remains tracked after an explicitly authorised stop-tracking repair;
- `.codex/config.toml` is unchanged unless the user explicitly requested a project model/reasoning override; when changed, it parses and unrelated settings are preserved;
- no application, environment, global config, or unrelated project file changed.

Show the exact Coordinator block after any `AGENTS.md` edit. Report whether any non-Coordinator line changed and revert incidental changes before completion.
