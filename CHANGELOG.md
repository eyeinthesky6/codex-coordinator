# Changelog

Notable changes to Codex Coordinator will be recorded here.

## Unreleased

## 0.1.7 - 2026-07-16

- Added task-fit model and reasoning guidance, run-wide user overrides, selective Ultra escalation, and safe future-turn retuning rules.
- Made explicit multi-agent delegation without Ultra a primary product value, while documenting normal Codex usage and concurrency limits.
- Prevented paused or idle worker tasks from being reused for unrelated goals, and added receiver-side mismatch return routing to a fresh task.
- Prepared the plugin and repository for the initial open-source release.
- Hardened restart-state parsing, stale ownership detection, and packaged hook discovery.
- Clarified enablement, first-run creation, archive recovery, routing, and shared-checkout ownership.
- Added the project logo, public architecture guide, and clearer install, fit, and first-success documentation.
- Added the public support funnel, lightweight governance policy, and explicit code ownership.
- Updated pinned GitHub Actions after reviewing their release notes and passing the full CI matrix.
