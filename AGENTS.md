# Repository guidance

Codex Coordinator is a small, dependency-free Codex plugin. Keep changes narrow, public-safe, and rooted in the existing package contract.

## Source of truth

- Plugin metadata: `plugins/codex-coordinator/.codex-plugin/plugin.json`
- Coordination behavior: `plugins/codex-coordinator/skills/codex-coordinator/`
- SessionStart hook: `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- Marketplace entry: `.agents/plugins/marketplace.json`
- Behavior and package checks: `tests/`

Read the relevant skill references and tests before changing protocol fields, ownership rules, routing, recovery, or hook output. Preserve existing contracts unless the change explicitly updates them and their tests.

## Working rules

- Keep the runtime on the Python standard library unless a real requirement justifies a dependency.
- Keep the SessionStart hook read-only, bounded, and free of network access.
- Do not add credentials, private task messages, user paths, or a project's live `.codex/coordination/` state.
- Keep mutable coordination state local. Only `.codex/coordination/project.yaml` is designed to be committed in an enabled project.
- Do not copy the Coordinator operating manual into projects that use the plugin.
- Update public documentation and tests with user-visible behavior.
- Avoid unrelated cleanup and generated audit artifacts.

## Validation

Run from the repository root:

```shell
python -m unittest discover -s tests -p "test_*.py" -v
```

Also parse changed JSON/YAML where practical and verify that relative package paths remain inside `plugins/codex-coordinator/`.

## Product development boundary

- An agent changing Coordinator product source must be explicitly user-authorised as a Maintainer with bounded source ownership.
- Installed global, local, legacy, cached, or marketplace-managed Coordinator core is never a product-development write target. Use the supported release update, reinstall, or Doctor recovery path instead.
