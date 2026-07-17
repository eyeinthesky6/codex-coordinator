# Local Mission Control

Mission Control is an optional, local-only dashboard for Codex Coordinator. It shows what Codex tasks are doing, what needs attention, and where active work may overlap before a commit.

It has no product login, cloud service, database server, telemetry, or JavaScript dependency. The Python standard library serves the dashboard on `127.0.0.1` and normally reads local Codex receipts plus Coordinator records without changing them. **Run Doctor** is its only explicit local write action.

## Run it

From the repository root:

```powershell
python -m apps.mission_control
```

The dashboard opens at `http://127.0.0.1:4317`. Use `--no-open` if you do not want it to open a browser automatically.

On Windows, leave it running in the background without installing a service:

```powershell
.\apps\mission_control\start-background.ps1
```

Background startup is quiet and idempotent: calling it again reuses the running server and does not open another browser tab. To open Mission Control explicitly while starting or reusing it, pass `-Open`:

```powershell
.\apps\mission_control\start-background.ps1 -Open
```

Stop that background process with:

```powershell
.\apps\mission_control\stop.ps1
```

Watch more Coordinator-enabled repositories by repeating `--project`:

```powershell
python -m apps.mission_control `
  --project C:\Projects\codex-coordinator `
  --project C:\Projects\another-project
```

## What it reads

- the local Codex thread index and bounded tails of task receipts under `CODEX_HOME`;
- each selected project's `.codex/coordination/project.yaml`, `CURRENT.md`, and active task records;
- declared write paths and recorded `apply_patch` edits for evidence-backed overlap warnings.

The dashboard never treats its display as coordination authority. Coordinator records remain the source of truth.

## Display contract

- Native Codex task names are the reviewer-facing labels and links. A canonical record with no native thread is labelled **Project coordination** rather than presenting its internal goal as a thread name.
- Every task card has one single-line **Next:** instruction. It tells the reviewer to act, wait, review, or resume without repeating the task transcript or Coordinator goal.
- A submitted user message is **Queued** until the receipt contains later agent reasoning, a response, or a tool call. Only that later evidence is labelled **Working now**.
- Coordinator records override status, blockers, ownership, and declared scope when a task is registered.
- A one-minute scan may update counts and freshness, but task order and reviewer actions stay stable so the workboard does not move while someone is reading it.
- Overlap means path evidence: declared scopes collide, an observed edit crosses another task's declared scope, or two active task receipts record edits to the same path. Merely working in the same project is not an alert.
- Overall and project tabs filter the metrics, workboard, and Action Center together.
- Only Coordinator-enabled projects appear. General Codex chats and arbitrary working folders are excluded from tabs, totals, the workboard, and actions.
- The Action Center is the only issue queue. It combines confirmed path conflicts with genuinely blocked or paused work, without duplicating the same signal across competing sections.
- A permanent feedback card links to the Codex Coordinator Telegram community. It stays visible across refreshes and project views, and does not write local response state.

The workboard uses read-only reviewer filters instead of draggable Kanban columns. Moving a card would imply that this dashboard can change Codex or Coordinator state; it cannot.

## Run Doctor

The Doctor panel lets the user start a bounded Coordinator health flow without opening another Codex task window. It runs ephemerally in the background and keeps the last result as no more than three short bullets. A green check appears only when Doctor explicitly reports a current installed Coordinator, no deferred project check, and no unresolved project finding; review and failure states use separate warning colors.

One click authorises only the Doctor contract: repair and validate the installed global Coordinator capability contract, skill, deterministic state helper, and exact SessionStart hook from the configured trusted package; scan locally discovered enabled projects, including verified missing heartbeat return paths for non-terminal work; and write deduplicated `DOCTOR_FINDING` records to affected private inboxes. Mission Control is tested by the repository suite and browser UAT, not recursively by Doctor. Doctor never edits canonical ownership, task files, enabled-project application code, Git, config, env, marketplaces, or managed plugin caches, and never creates, messages, or wakes a task.

Installed-plugin repair and verification are deterministic and use no model tokens. When enabled projects need coordination interpretation, Doctor requests one ephemeral GPT-5.6 Sol pass with Medium reasoning and a compact non-terminal task inventory. Mission Control never downgrades Doctor to an older model family. If the `codex` executable on `PATH` is too old for Sol, the run fails with an upgrade message instead of silently changing models.

All browser requests must use a localhost host name. Write endpoints also require JSON and reject cross-site browser origins, so another website cannot trigger Doctor or change local settings.

## Refresh and token use

- The local scan defaults to every **1 minute** and uses **zero model tokens**.
- The Settings panel can slow the local refresh.
- Scans, counts, filters, task summaries, and Action Center updates are deterministic local work and never call a model.
- Doctor is the only model-backed Mission Control action, and it runs only when the user clicks **Run Doctor**.

Local settings and Doctor results are kept outside the repository in the operating system's local application-data folder.

## Current boundary

This first version is for one machine. Its active/finished state is inferred from bounded local Codex receipts; Coordinator task records add the stronger assignment, pause, blocker, and file-ownership context. A future team version can send redacted snapshots from each machine to a shared dashboard without changing the local collector contract.
