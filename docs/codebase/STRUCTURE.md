# Structure

## Public repository surface

- `README.md`: product promise, fit, installation, and first use.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `SECURITY.md`: contributor and support routes.
- `CHANGELOG.md`: release-facing change history.
- `AGENTS.md`: instructions for agents and contributors working in this repository.
- `site/`: static GitHub Pages front door, crawler policy, and sitemap.
- `llms.txt`: small agent-readable map of the canonical public documentation.
- `docs/DISCOVERY.md`: problem-led recommendation, non-fit, proof, and comparison guidance.
- `docs/codebase/`: contributor-facing technical map.

## Distributable plugin

- `plugins/codex-coordinator/.codex-plugin/plugin.json`: package identity and Codex interface metadata.
- `plugins/codex-coordinator/assets/logo.png`: canonical brand asset.
- `plugins/codex-coordinator/skills/codex-coordinator/SKILL.md`: top-level routing and operating contract.
- `plugins/codex-coordinator/skills/codex-coordinator/capabilities.json`: machine-checked installed behavior contract used by Doctor.
- `plugins/codex-coordinator/skills/codex-coordinator/scripts/coordination_state.py`: deterministic current-state, reconciliation, create-if-absent, and two-phase inbox-hash checkpoint helper.
- `plugins/codex-coordinator/skills/codex-coordinator/references/`: short operations router plus execution, reconciliation, messaging, installation, recovery, maintenance, and Doctor lanes loaded as needed.
- `plugins/codex-coordinator/skills/codex-coordinator/agents/openai.yaml`: agent-facing display metadata and default prompt.
- `plugins/codex-coordinator/hooks/hooks.json`: SessionStart registration.
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`: read-only restart-context hook.
- `plugins/codex-coordinator/scripts/codex_coordinator_doctor.py`: atomic repair plus installed skill and hook validation for the configured Coordinator runtime, with optional Mermaid diagnostic output.
- `plugins/codex-coordinator/LICENSE`: license included with the distributed plugin.

## Marketplace and validation

- `.agents/plugins/marketplace.json`: repository marketplace entry pointing to the local plugin directory.
- `tests/test_package_contract.py`: manifest, license, asset, hook, and skill-link checks.
- `tests/test_session_start.py`: behavioral and safety checks for restart parsing, table semantics, duplicate ownership, and fail-closed transitions.
- `tests/test_doctor.py`: update-package identity, unambiguous JSON, non-overlapping destinations, atomic installed-runtime repair, rollback, preservation, runtime validation, idempotency, and Mermaid-projection checks.
- `tests/test_coordination_state.py`: state metadata and row validation, safe taskless normalization, reconciliation routing and ledger validation, non-overwriting file creation, and fail-safe inbox checkpoint behavior.
- `tests/test_public_site.py`: public metadata, route, asset-assembly, and discovery-file checks.
- `.github/`: issue forms, pull-request template, CI, Pages deployment, and dependency automation.

## Evidence

- `.agents/plugins/marketplace.json`
- `plugins/codex-coordinator/`
- `tests/test_package_contract.py`
- `tests/test_session_start.py`
- `tests/test_doctor.py`
- `tests/test_public_site.py`
- `site/`
- `.github/`
