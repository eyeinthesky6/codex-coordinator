# Integrations

## OpenAI Codex

The repository is packaged as a Codex plugin. The marketplace manifest points to the plugin directory, whose manifest exposes one skill, interface metadata, brand assets, and a SessionStart hook. Users invoke the skill explicitly. Codex's native task tools create, read, message, pin, rename, archive, fork, and hand off durable user-visible tasks; native heartbeats wake the Coordinator while a goal is live. Collaboration subagents remain available inside a registered task, while their parent retains canonical ownership and reporting.

Hook trust remains a user decision. Codex may skip an untrusted or changed hook until the user reviews it.

### Deferred Codex Goals review

The current product does not integrate with Codex Goals and does not depend on Goals for task completion or recovery. A later version may evaluate Goals as an optional, capability-detected continuity aid inside the Coordinator task. Project documents, ownership records, inbox reconciliation, native task status, and the existing heartbeat remain authoritative.

Any trial must use only a supported host surface, default off, avoid private Codex databases and transport internals, require no project-schema migration, and fall back cleanly when the capability changes or disappears. It must not introduce an autonomous-completion claim. The private product roadmap contains the experiment gates and acceptance questions; this section records only the integration boundary.

## Mission Control

The optional Mission Control companion is distributed through the tagged source repository. Its standard-library server binds to localhost and reads bounded local Codex task receipts plus Coordinator project records. **Run Doctor** repairs the installed package and performs a deterministic zero-model structured-state check; it is not part of the plugin hook and does not become project authority. The separate user-triggered **Deep Review** sends only a capped allowlisted task-contract packet to the configured model at Low reasoning and returns candidate-only semantic review with no project write authority.

## Git

The plugin uses Git only for repository and worktree context. The restart hook runs a bounded `git worktree list --porcelain -z` query to locate the primary worktree. It does not create branches, commits, or worktrees.

## GitHub

The canonical repository is `https://github.com/eyeinthesky6/codex-coordinator`. It includes GitHub Actions, Dependabot configuration, a bug form, Discussion routes, a pull-request template, releases, and a static Pages front door.

The public repository uses a protected `main` branch with four required Python matrix checks plus the required Secret scan. Force pushes and branch deletion are disabled, conversations must be resolved, default workflow permissions are read-only, private vulnerability reporting is available, and Discussions are enabled with Q&A and Ideas routes.

`.github/workflows/pages.yml` assembles `site/`, `llms.txt`, and the canonical plugin logo into one GitHub Pages artifact. The workflow uses pinned actions and grants write and identity permissions only to the deploy job. The site is not part of the plugin runtime.

Provider controls can change independently of the repository. Read them back before a release instead of treating this document as proof of current settings.

## Network and external services

The distributed plugin has no service, database, telemetry client, or network call. Mission Control is a separate opt-in localhost process with no product login, cloud service, or telemetry. GitHub is repository hosting and automation, not a plugin runtime dependency.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/.codex-plugin/plugin.json`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `apps/mission_control/`
- `.github/`
- `.github/workflows/pages.yml`
- `site/`
