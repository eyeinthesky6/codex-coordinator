# Integrations

## OpenAI Codex

The repository is packaged as a Codex plugin. The marketplace manifest points to the plugin directory, whose manifest exposes one skill, interface metadata, brand assets, and a SessionStart hook. Users invoke the skill explicitly; Codex's native task and collaboration tools perform actual task execution and messaging.

Hook trust remains a user decision. Codex may skip an untrusted or changed hook until the user reviews it.

## Git

The plugin uses Git only for repository and worktree context. The restart hook runs a bounded `git worktree list --porcelain -z` query to locate the primary worktree. It does not create branches, commits, or worktrees.

## GitHub

The canonical repository is `https://github.com/eyeinthesky6/codex-coordinator`. It includes GitHub Actions, Dependabot configuration, a bug form, Discussion routes, and a pull-request template.

The initial CI matrix, Dependabot alerts and fixes, Issues, Discussions, topics, merge policy, and read-only Actions permissions have been verified while the repository is private.

[TODO] After the repository becomes public, enable and verify branch protection, required checks, secret scanning, push protection, and private vulnerability reporting.

## Network and external services

The distributed plugin has no service, database, telemetry client, or network call. GitHub is repository hosting and automation, not a runtime dependency.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/.codex-plugin/plugin.json`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `.github/`
