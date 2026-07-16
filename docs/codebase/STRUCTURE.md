# Structure

## Public repository surface

- `README.md`: product promise, fit, installation, and first use.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `SECURITY.md`: contributor and support routes.
- `CHANGELOG.md`: release-facing change history.
- `AGENTS.md`: instructions for agents and contributors working in this repository.
- `docs/codebase/`: contributor-facing technical map.

## Distributable plugin

- `plugins/codex-coordinator/.codex-plugin/plugin.json`: package identity and Codex interface metadata.
- `plugins/codex-coordinator/assets/logo.png`: canonical brand asset.
- `plugins/codex-coordinator/skills/codex-coordinator/SKILL.md`: top-level routing and operating contract.
- `plugins/codex-coordinator/skills/codex-coordinator/references/`: installation, operations, recovery, and maintenance details loaded as needed.
- `plugins/codex-coordinator/skills/codex-coordinator/agents/openai.yaml`: agent-facing display metadata and default prompt.
- `plugins/codex-coordinator/hooks/hooks.json`: SessionStart registration.
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`: read-only restart-context hook.
- `plugins/codex-coordinator/LICENSE`: license included with the distributed plugin.

## Marketplace and validation

- `.agents/plugins/marketplace.json`: repository marketplace entry pointing to the local plugin directory.
- `tests/test_package_contract.py`: manifest, license, asset, hook, and skill-link checks.
- `tests/test_session_start.py`: behavioral and safety checks for restart parsing.
- `.github/`: issue forms, pull-request template, CI, and dependency automation.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/`
- `tests/test_package_contract.py`
- `tests/test_session_start.py`
- `.github/`
