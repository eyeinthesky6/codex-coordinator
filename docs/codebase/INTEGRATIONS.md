# Integrations

## OpenAI Codex

The repository is packaged as a Codex plugin. The marketplace manifest points to the plugin directory, whose manifest exposes one skill, interface metadata, brand assets, and a SessionStart hook. Users invoke the skill explicitly. Codex's native task tools create, read, message, pin, rename, archive, fork, and hand off durable user-visible tasks; native heartbeats wake the Coordinator while a goal is live. Collaboration subagents remain available inside a registered task, while their parent retains canonical ownership and reporting.

Hook trust remains a user decision. Codex may skip an untrusted or changed hook until the user reviews it.

## Git

The plugin uses Git only for repository and worktree context. The restart hook runs a bounded `git worktree list --porcelain -z` query to locate the primary worktree. It does not create branches, commits, or worktrees.

## GitHub

The canonical repository is `https://github.com/eyeinthesky6/codex-coordinator`. It includes GitHub Actions, Dependabot configuration, a bug form, Discussion routes, a pull-request template, releases, and a static Pages front door.

The public repository uses a protected `main` branch with four required Python matrix checks plus the required Secret scan. Force pushes and branch deletion are disabled, conversations must be resolved, default workflow permissions are read-only, private vulnerability reporting is available, and Discussions are enabled with Q&A and Ideas routes.

`.github/workflows/pages.yml` assembles `site/`, `llms.txt`, and the canonical plugin logo into one GitHub Pages artifact. The workflow uses pinned actions and grants write and identity permissions only to the deploy job. The site is not part of the plugin runtime.

Provider controls can change independently of the repository. Read them back before a release instead of treating this document as proof of current settings.

## Network and external services

The distributed plugin has no service, database, telemetry client, or network call. GitHub is repository hosting and automation, not a runtime dependency.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/.codex-plugin/plugin.json`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `.github/`
- `.github/workflows/pages.yml`
- `site/`
