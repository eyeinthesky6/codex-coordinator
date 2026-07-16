<p align="center">
  <img src="plugins/codex-coordinator/assets/logo.png" alt="Codex Coordinator logo" width="160">
</p>

<h1 align="center">Codex Coordinator</h1>

<p align="center"><strong>Launch and coordinate multiple Codex agents for one large goal—even without Ultra.</strong></p>

Codex Coordinator turns a large repository goal into bounded work for multiple Codex agents, then keeps that parallel work understandable: who owns each change, what is waiting, and how another task can safely continue after a pause or restart.

Each working task keeps one core goal. Finishing a turn or pausing does not turn that task into a general-purpose worker: unrelated work gets a new Codex task, so its conversation and activity remain easy to follow. If a mismatched assignment reaches a worker, it leaves the current goal unchanged and asks the Coordinator to route the work elsewhere.

> **Independent project:** Codex Coordinator is a third-party plugin for OpenAI Codex. It is not affiliated with, endorsed by, or maintained by OpenAI. Codex and related OpenAI product names belong to OpenAI.

It is for builders running several independent Codex tasks in the same Git repository who are tired of manually relaying ownership and handoffs. It uses small repository records, Codex's native task tools, and one read-only restart hook—no service, database, dashboard, or lock manager.

## Multi-agent work without Ultra

Ultra can proactively decide when to delegate work, but it is not required to run parallel agents. At other supported intelligence levels, Codex delegates when the user asks directly or when applicable project or skill instructions request it. Codex Coordinator supplies that explicit multi-agent workflow: give it one large goal and it creates the minimum bounded tasks needed, assigns them to separate agents, and keeps their ownership and results traceable.

The plugin does not bypass Codex plan availability, usage, token, or concurrency limits. Parallel agents consume more usage than a comparable single-agent run. See the official [Codex subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents).

### Model and reasoning choices

The Coordinator records a model and reasoning choice for each task. If the user supplies an exact per-task or run-wide preference, that preference wins within the models and reasoning levels supported by the account and destination host. For example:

```text
Use my preferred model at Extra High for all workers. Use Ultra only when it materially helps.
```

That instruction applies to the current coordinated goal without rewriting global or project configuration. Without an override, the Coordinator matches the task to a fast, balanced, or strongest suitable model and uses more reasoning only as complexity and risk justify it. On Codex surfaces that require the user to name a specific model, the Coordinator proposes an exact combination for approval or inherits the configured default.

The Coordinator itself should normally use the strongest suitable model with High reasoning. Extra High is reserved for difficult decomposition, recovery, or integration decisions; Ultra remains optional and selective.

**Status:** pre-release. The package is being hardened for its first public release.

[![CI](https://github.com/eyeinthesky6/codex-coordinator/actions/workflows/ci.yml/badge.svg)](https://github.com/eyeinthesky6/codex-coordinator/actions/workflows/ci.yml)

## When it fits

Use Codex Coordinator when:

- you want to launch multiple agents from one large goal without relying on Ultra's proactive delegation;
- two or more Codex tasks may touch related parts of one repository;
- work needs an explicit owner, handoff, or blocked state;
- tasks pause, compact, or restart and still need a shared picture;
- you want coordination state scoped to the repository instead of a separate service.

You probably do not need it for one task, a small isolated edit, or work where Git branches alone already make ownership obvious. It is also not a cross-machine project manager.

## How it relates to existing tools

| Tool | What it owns |
|---|---|
| Codex tasks and agents | Execute and discuss the work |
| Git branches and worktrees | Isolate files and changes |
| Codex Coordinator | Record repository-scoped ownership, routing, and handoffs |

Coordinator complements native Codex agents and Git worktrees; it does not replace them.

## Requirements

- Codex with plugin and hook support;
- Git;
- Python 3.10 or newer available as `python` on Windows and `python3` on macOS or Linux.

## Install from a local checkout

1. Add this directory as a marketplace:

   ```powershell
   codex plugin marketplace add <path-to-this-directory>
   ```

2. Open Codex Plugins and install **Codex Coordinator** from the `codex-coordinator` marketplace.
3. Review and trust the SessionStart hook when Codex asks. It reads only the local project marker and current coordination state, makes no network calls, and adds restart context without writing files. In the CLI, use `/hooks`; an untrusted hook is skipped.
4. Start a new Codex task and run:

   ```text
   Use $codex-coordinator to create the tasks needed and coordinate this goal: <goal>
   ```

The first useful coordinated task lazily enables that Git repository. Small, isolated work continues without extra coordination files. To opt a repository out, say:

```text
Turn Codex Coordinator off for this repository.
```

### What first success looks like

For a coordination-worthy goal, Codex should explain the task split and current owners. The repository gains a trackable `.codex/coordination/project.yaml` marker plus local, Git-ignored current state. After a restart, the hook restores a short handoff summary; it never grants ownership by itself.

Try these follow-up prompts:

```text
Show who is working on what and what is blocked.
Hand off <task> to <registered task name>.
Reconcile the current coordination state.
```

## What it creates in an enabled repository

- `.codex/coordination/project.yaml`: trackable discovery marker and stable project identity—the only coordination file intended for Git;
- `.codex/coordination/CURRENT.md`: local current ownership and handoff state;
- task and suggestion records only when real work requires them;
- one minimal discovery block in the root `AGENTS.md`;
- a narrow root `.gitignore` block that keeps mutable coordination state local.
- missing `model` and `model_reasoning_effort` defaults in `.codex/config.toml`; existing explicit choices and unrelated settings are preserved.

The plugin never copies its operating manual into projects. It does not grant Git, deployment, database, environment, or application authority; project tasks receive those boundaries explicitly.

## Package layout

- `plugins/codex-coordinator/skills/codex-coordinator/`: progressively loaded behavior;
- `plugins/codex-coordinator/hooks/hooks.json`: restart-hook registration;
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`: read-only restart context;
- `.agents/plugins/marketplace.json`: local or Git marketplace entry.

For a deeper contributor map, see [architecture](docs/codebase/ARCHITECTURE.md), [structure](docs/codebase/STRUCTURE.md), [testing](docs/codebase/TESTING.md), and [known concerns](docs/codebase/CONCERNS.md).

## Limits

- Coordination is repository-scoped; messages from another project are ignored.
- A worker task is not reused for an unrelated goal, even while paused or idle; unrelated work needs a new native Codex task.
- Mutable task state is local to a checkout and is not synchronized between machines.
- The hook supplies restart context but never grants ownership; repository state remains authoritative.
- A changed hook must be reviewed and trusted again.
- Codex Coordinator coordinates Codex tasks; it does not replace Codex agents or Codex's native task system.
- The plugin does not make Git, deployment, database, environment, or provider decisions for a task.

## Development

Run the dependency-free test suite:

```powershell
python -m unittest discover -s tests -v
```

For an optional local secret check, install pre-commit and its hook (CI runs a separate Gitleaks scan):

```powershell
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md), and the [codebase guide](docs/codebase/STRUCTURE.md).

## Update

Refresh the marketplace, update or reinstall the plugin in Codex Plugins, review the changed hook, and start a new task:

```powershell
codex plugin marketplace upgrade codex-coordinator
```

An update replaces only the plugin-managed package or cache. It does not rewrite project files or live project state. When migrating from a manual installation, verify the plugin first, then remove the legacy skill and hook so both copies do not run.

## Feedback

Use [Q&A](https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/q-a) for usage help and [Ideas](https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/ideas) for early requests. Open an Issue only for a reproducible bug or accepted, scoped work. Follow [SECURITY.md](SECURITY.md) for vulnerabilities and never paste private task messages or live coordination state into a public report.

## License

[MIT](LICENSE) © 2026 Six Ideas.
