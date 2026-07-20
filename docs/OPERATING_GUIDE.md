# Codex Coordinator operating guide

Use this page to choose the smallest tool that matches the job. You do not need to run Coordinator,
Mission Control, Doctor, and the test suite for every change: they answer different questions.

## Choose by outcome

| What you need | Use | How |
|---|---|---|
| One small, isolated Codex change | A normal Codex task | Ask for the change normally. Coordinator should stay out of the way. |
| Several substantial Codex tasks in one repository | Codex Coordinator | Ask Codex to coordinate the bounded goal, for example: `Use $codex-coordinator to coordinate the release-readiness work in this repository.` |
| A local view of current project work | Mission Control | It starts after the first Coordinator session, or ask Codex to `Start Mission Control`. |
| Check whether the installed Coordinator is current | Doctor check | Run the Doctor with `--check`; this is read-only. |
| Repair a drifted manual Coordinator installation | Doctor apply | Review the trusted source package, then explicitly run the Doctor with `--apply`. |
| Prove the source package still behaves correctly | Repository tests | Run the full Python test suite. |
| Prove installation on a new machine | Fresh-machine UAT | Follow the stable install instructions in the README on a clean supported machine. |
| Install or update the plugin | Marketplace install/update | Follow the pinned stable-release instructions in the README. |
| Turn Coordinator off for one repository | Reversible project deactivation | Ask Codex to turn it off; inspect the dry run before exact project and native lifecycle changes are applied. |
| Remove Coordinator globally | Verified global uninstall | Plan from explicitly known or indexed repositories, deactivate each safely, stop Mission Control, then remove the plugin. |
| Delete saved Coordinator history | Explicit purge | Name the exact project or global application-data boundary and accept that recovery history will be lost. |

## The normal daily flow

### Small work

Open a normal Codex task and describe the result you want. No setup command is required. An enabled
repository does not turn every small task into multi-agent work.

### Coordinated work

Give Codex one shared outcome and the important limits:

```text
Use $codex-coordinator to coordinate this repository's release-readiness work.
Keep the public API stable, do not publish anything, and give me one consolidated result.
```

Coordinator decides whether the work is large enough to need durable worker tasks. It should keep
routine tests, lookups, and mechanical documentation inside the current owner instead of creating a
new task for every command. It records whether it reused a same-area owner, retained a microtask,
delegated substantial independent work, or created a task for a genuinely new area. It may choose a
bounded linked worktree when an independent writer would otherwise wait, while the primary worktree
keeps canonical coordination state and one integration owner remains named.

Coordinator-generated tasks inherit the user's configured model. They use Low reasoning for
deterministic work or Medium for normal work unless managed policy or the user explicitly overrides
it. Expensive reasoning is not required for coordination.

### Observe current work

Mission Control is optional. It reads local Codex and Coordinator records and displays a local
dashboard; it does not become the project authority. The bundled server starts on the first valid
Coordinator session and later sessions reuse it without opening duplicate tabs.

After Coordinator is enabled for a repository, one pinned Coordinator remains registered and all same-repository tasks are managed by default. Only the user may exclude a task. A user pause changes the project to report-only mode: observation and summaries continue, but assignment, redirection, wake, stop, resume, and ownership changes stop. Workload idle keeps the Coordinator and repository heartbeat. Each Coordinator summary and Mission Control project view shows the mode and exclusions.

From chat:

```text
Start Mission Control.
Stop Mission Control.
```

Stopping it from chat or the Settings panel disables automatic restart. An explicit chat start
turns automatic startup back on. For source development, the direct command remains:

```powershell
python -m apps.mission_control
```

Windows background mode:

```powershell
.\apps\mission_control\start-background.ps1 -Open
.\apps\mission_control\stop.ps1
```

Watch more than one enabled project:

```powershell
python -m apps.mission_control `
  --project C:\Projects\project-one `
  --project C:\Projects\project-two
```

See the [Mission Control guide](../apps/mission_control/README.md) for settings, token use, Doctor,
and privacy boundaries.

## Health, repair, and proof

These checks are not interchangeable:

| Check | What it proves | What it does not prove |
|---|---|---|
| Doctor | The installed global Coordinator contract, skill, helper, and hook match a trusted package and pass bounded installation checks | Mission Control behavior, source-repository quality, release readiness, or user success |
| Repository tests | The checked-out source passes its automated behavior and package contracts | A clean install on another machine or a successful public release |
| Mission Control | Current local observation and dashboard behavior | Canonical ownership or task permission |
| Fresh-machine UAT | A user can install and reach first value in a clean environment | Ongoing compatibility with every future Codex release |

### Doctor: read-only check

From the trusted source checkout:

```powershell
python plugins\codex-coordinator\scripts\codex_coordinator_doctor.py --check
```

For a compact automation-friendly result:

```powershell
python plugins\codex-coordinator\scripts\codex_coordinator_doctor.py --compact --check
```

For a private visual projection of the same result:

```powershell
python plugins\codex-coordinator\scripts\codex_coordinator_doctor.py `
  --check `
  --mermaid-out C:\private\coordinator-doctor.mmd
```

The Mermaid file helps a person navigate the result. JSON, exit status, hashes, syntax checks, and
the hook smoke test remain the proof.

### Doctor: approved repair

`--apply` writes to the configured installed skill and hook. Use it only after the source checkout is
the exact trusted package you intend to install:

```powershell
python plugins\codex-coordinator\scripts\codex_coordinator_doctor.py --apply
python plugins\codex-coordinator\scripts\codex_coordinator_doctor.py --check
```

Start a new Codex task after an installed-skill update so the new instructions are loaded. Doctor
does not change project ownership, application code, Git state, configuration, environment files,
or Mission Control.

### Repository tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Run the full suite after changes to the packaged skill, hook, Doctor, Mission Control, marketplace
metadata, or tests. Focused tests may shorten development, but the full suite is the repository gate.

## Install, update, and first success

Use the [README quick start](../README.md#quick-start) for the current stable install path. After an
update, start a new Codex task. A project with `coordination_enabled: true` reuses its existing local
state; an update must not reset its work or ownership.

First success is a real bounded goal that is easier to follow because Coordinator kept ownership and
status clear. Installation alone, an empty demo, a green Doctor result, or an open dashboard is not
user success.

## Deactivation and uninstall

These are different operations:

| Operation | Default result |
|---|---|
| Pause management | Repository remains enabled in report-only mode; Coordinator observes and reports but performs no control actions. |
| Deactivate project | Marker is disabled, exact discovery block and repository heartbeat are removed, history and configuration are preserved. |
| Uninstall globally | Every verified intended project is deactivated independently, Mission Control is stopped, exact Coordinator heartbeats and plugin are removed, history is preserved. |
| Purge | Exact saved project or global Coordinator data is removed only under separate explicit confirmation. |

From chat, prefer:

```text
Turn Codex Coordinator off for this repository.
Uninstall Coordinator globally but preserve project history.
```

For development or recovery, run the packaged helper without `--apply` first:

```powershell
python plugins\codex-coordinator\scripts\codex_coordinator_uninstall.py `
  project deactivate --project-root C:\Projects\example

python plugins\codex-coordinator\scripts\codex_coordinator_uninstall.py `
  global-plan --codex-home $env:CODEX_HOME `
  --project-root C:\Projects\example
```

The helper changes only verified project files when explicitly applied. It reports, but does not
pretend to perform, native task archival/pinning, automation deletion, Mission Control shutdown, or
plugin removal. Global planning never scans a drive. See the
[uninstall and deactivation contract](codebase/UNINSTALL_AND_DEACTIVATION.md) for preservation,
retry, purge, and disposable-VM testing boundaries.

## Which document is authoritative?

| Question | Source of truth |
|---|---|
| What users install and how they start | [README](../README.md) |
| Coordinator behavior and boundaries | [Packaged skill](../plugins/codex-coordinator/skills/codex-coordinator/SKILL.md) and its selected reference lane |
| Mission Control behavior | [Mission Control guide](../apps/mission_control/README.md) and its tests |
| Current source architecture | [Architecture](codebase/ARCHITECTURE.md) and implementation |
| Test commands and coverage | [Testing guide](codebase/TESTING.md) and `tests/` |
| Support, bugs, community, and security routes | [Support](../SUPPORT.md) and [Security](../SECURITY.md) |

When documentation and implementation disagree, do not guess. Verify the behavior, then update the
smallest owning document and its tests.

## Safety boundaries

- Normal diagnosis is read-only. `--apply`, publishing, releases, external replies, and account or
  community changes need the applicable approval.
- Mission Control is an observer. Coordinator documents and native Codex task state retain authority.
- Do not publish local coordination state, task messages, private plans, credentials, or recovery
  information.
- Do not run every tool “for safety.” Choose the check that proves the claim you need.
