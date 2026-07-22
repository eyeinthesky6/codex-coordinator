# Structure

## Boundary core

- `plugins/codex-coordinator/.codex-plugin/plugin.json`: package and public prompt metadata.
- `plugins/codex-coordinator/hooks/hooks.json`: direct five-second SessionStart registration.
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`: marker-only, read-only hook.
- `plugins/codex-coordinator/skills/codex-coordinator/SKILL.md`: boundary-board invariants and lane router.
- `plugins/codex-coordinator/skills/codex-coordinator/capabilities.json`: schema-21, 18-field public behavior contract.
- `plugins/codex-coordinator/skills/codex-coordinator/scripts/coordination_state.py`: active claim list/claim/release helper.
- `plugins/codex-coordinator/skills/codex-coordinator/references/`: execution, messaging, recovery, installation, maintenance, and Doctor guidance.
- `plugins/codex-coordinator/scripts/codex_coordinator_doctor.py`: manual read-only compatibility check.
- `plugins/codex-coordinator/scripts/codex_coordinator_uninstall.py`: dry-run-first schema-2 lifecycle and legacy schema-1 cleanup planning.

## Project state

- `.codex/coordination/project.yaml`: committed opt-in marker.
- `.codex/coordination/active/<thread-uuid>.json`: ignored active task-owned claims.
- `.codex/coordination/archive/<thread-uuid>-<time>.json`: ignored compact cold receipts.
- Schema-1 `CURRENT.md`, tasks, inbox, and cache may remain as preserved ignored history but are not schema-2 authority.

## Optional observer boundary

The base package contains no Mission Control runtime, UI, launcher, lifecycle helper, or browser test. The removed schema-1 implementation remains available from `v0.3.0` and Git history. Any future observer requires a separate package and must consume only the public schema-2 board.

## Public and contributor docs

- `README.md`: current source behavior and unreleased status.
- `docs/OPERATING_GUIDE.md`: operator commands and boundaries.
- `docs/DISCOVERY.md`: when to recommend the board or a simpler path.
- `docs/codebase/2026-07-21_boundary-board-simplification_architectural_review.md`: exhaustive decision history.
- `CHANGELOG.md`: chronological behavior changes.
- `PRIVACY.md`, `TERMS.md`, `SECURITY.md`: public trust boundaries.

## Tests

- `test_coordination_state.py`: task-owned records, overlap, concurrency, limits, privacy, and cold receipts.
- `test_session_start.py`: silent opt-out, bounded hint, malformed markers, and no launcher.
- `test_doctor.py`: read-only package compatibility and reinstall-only failure.
- `test_uninstall.py`: schema-2 no-lifecycle behavior, legacy cleanup, preservation, and purge confirmation.
- `test_package_contract.py`, `test_goal_leadership_contract.py`: architecture and guidance regression gates.
- `test_mission_control*.py`, `test_doctor_scan.py`: absence and optional-tool isolation from the base runtime.
- Public site, release, and hygiene tests cover distribution surfaces separately.
