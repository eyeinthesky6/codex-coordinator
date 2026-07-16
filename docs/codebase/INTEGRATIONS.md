# Integrations

## OpenAI Codex

The repository is packaged as a Codex plugin. The marketplace manifest points to the plugin directory, whose manifest exposes one skill, interface metadata, brand assets, and a SessionStart hook. Users invoke the skill explicitly; Codex's native task and collaboration tools perform actual task execution and messaging.

Hook trust remains a user decision. Codex may skip an untrusted or changed hook until the user reviews it.

## Git

The plugin uses Git only for repository and worktree context. The restart hook runs a bounded `git worktree list --porcelain -z` query to locate the primary worktree. It does not create branches, commits, or worktrees.

## GitHub

The repository includes GitHub Actions, Dependabot configuration, issue forms, and a pull-request template. These become active only after the repository is hosted on GitHub.

[TODO] Add the canonical repository URL after the public remote exists.

[TODO] Verify branch protection, required CI, secret scanning, private vulnerability reporting, Discussions, and issue routes on the live repository before launch.

## Network and external services

The distributed plugin has no service, database, telemetry client, or network call. GitHub is repository hosting and automation, not a runtime dependency.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/.codex-plugin/plugin.json`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `.github/`
