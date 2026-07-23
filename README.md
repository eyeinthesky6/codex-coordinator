<h1 align="center">Codex Coordinator</h1>

<p align="center"><strong>Run several Codex tasks without becoming their full-time project manager.</strong></p>

<p align="center">
  <a href="https://github.com/eyeinthesky6/codex-coordinator/actions/workflows/ci.yml"><img alt="CI status" src="https://github.com/eyeinthesky6/codex-coordinator/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/eyeinthesky6/codex-coordinator/releases/tag/v0.4.0"><img alt="Latest release" src="https://img.shields.io/badge/release-v0.4.0-1f6b5c"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-17231f"></a>
</p>

Running several Codex tasks sounds useful until two of them solve the same problem, one changes work another still needs, and you start opening every window just to understand what is happening.

Codex Coordinator gives those tasks a few clear jobs and a simple picture of who owns what. It helps you catch work that may collide before it becomes rework—without a background manager or a second place for your conversations.

**[Website](https://eyeinthesky6.github.io/codex-coordinator/)** · **[Install](#install)** · **[FAQ](https://eyeinthesky6.github.io/codex-coordinator/faq.html)** · **[Ask a question](https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/q-a)**

## What it takes off your plate

- Checking every task window to find out who is doing what.
- Relaying ordinary status updates between related tasks.
- Discovering too late that two tasks started overlapping work.
- Guessing who still owns a job after a task pauses or restarts.
- Creating a fresh task when an existing related task already has useful context.

Codex still does the work. Git still keeps the history. You still decide what gets changed or published.

## How it works

1. **Give it one repository outcome.** Describe the result you want rather than splitting it into tiny commands yourself.
2. **Keep each task focused.** Coordinator reuses a suitable related task when possible and gives every task a complete job.
3. **Ask for the current picture.** See what is active, blocked, finished, or likely to overlap without checking every window.

| Ask | Work | Review |
|---|---|---|
| ![One goal becomes a few clear tasks](site/assets/demos/01-ask-and-split.gif) | ![Several tasks work on separate jobs](site/assets/demos/02-tasks-at-work.gif) | ![The current result is brought into one view](site/assets/demos/03-one-result.gif) |

## When it helps

Use Codex Coordinator when two or three durable Codex tasks may work in the same repository and unclear ownership would create real rework.

Keep your workflow simpler when:

- one task can finish the job safely;
- you only need a quick answer or small edit;
- a short-lived helper can report directly back to one parent task;
- separate branches or worktrees already give you all the isolation you need.

## Install

Requirements: OpenAI Codex with plugin support, Git, and Python 3.10 or newer.

Add the current stable release and install it:

```powershell
codex plugin marketplace add eyeinthesky6/codex-coordinator --ref v0.4.0
codex plugin add codex-coordinator@codex-coordinator
```

Then open a repository in Codex and ask:

```text
Use $codex-coordinator to coordinate this project goal:
<describe the outcome you want>
```

Installation does not turn Coordinator on for every repository. You choose where to use it.

You can also find it in the [ChatGPT Plugins directory](https://chatgpt.com/plugins/plugins_6a5c8cb6a5648191a43a76e6a1e637d8) and on [skills.sh](https://skills.sh/eyeinthesky6/codex-coordinator/codex-coordinator).

## What it does not add

- No background monitoring or constant status checks.
- No copied prompts, chats, reasoning, or tool output.
- No automatic worktree or branch creation.
- No required pull-request workflow.
- No separate dashboard, database, account, or cloud service.
- No permission to deploy, publish, change environments, or override your decisions.

## Privacy and control

Task conversations remain in Codex. Coordinator keeps only a small amount of local project information needed to show the active job and planned work for each task.

It does not upload source code, prompts, chats, reasoning, or tool output. The project has no product telemetry and no coordination server.

Read the full [privacy policy](PRIVACY.md), [security policy](SECURITY.md), and [technical design](https://eyeinthesky6.github.io/codex-coordinator/developers.html).

## For developers and maintainers

The user-facing story stays deliberately simple. Implementation details, lifecycle rules, validation, migration, and architecture history live here:

- [Developer guide](https://eyeinthesky6.github.io/codex-coordinator/developers.html)
- [Operating guide](docs/OPERATING_GUIDE.md)
- [Architecture](docs/codebase/ARCHITECTURE.md)
- [Testing](docs/codebase/TESTING.md)
- [Design history and simplification decision](docs/codebase/2026-07-21_boundary-board-simplification_architectural_review.md)
- [Shared-checkout correction](docs/codebase/2026-07-23_cooperative-shared-checkout_architectural_review.md)
- [Changelog](CHANGELOG.md)

Run the complete test suite from the repository root:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Community

- Ask usage questions in [Q&A](https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/q-a).
- Share real workloads and early requests in [Ideas](https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/ideas).
- Report reproducible bugs through [Issues](https://github.com/eyeinthesky6/codex-coordinator/issues).
- Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing code.
- Use [SECURITY.md](SECURITY.md) for private vulnerability reports.

Never post credentials, private task messages, personal paths, or live project state in a public issue or discussion.

## License

[MIT](LICENSE) © 2026 Six Ideas.

Codex Coordinator is an independent third-party project and is not affiliated with or endorsed by OpenAI.
