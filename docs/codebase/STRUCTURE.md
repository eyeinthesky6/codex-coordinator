# Structure

## Boundary core

- `plugins/codex-coordinator/.codex-plugin/plugin.json`: package and public prompt metadata.
- `plugins/codex-coordinator/hooks/hooks.json`: direct five-second SessionStart, UserPromptSubmit, and Stop registrations.
- `plugins/codex-coordinator/scripts/codex_coordinator_prompt_guard.py`: prompt-time guard for assignment identity and local repository placement.
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`: bounded read-only hook for the marker and exact current task's pending-delivery filename count.
- `plugins/codex-coordinator/scripts/codex_coordinator_stop_guard.py`: one-shot, read-only exact-own-claim lifecycle guard.
- `plugins/codex-coordinator/skills/codex-coordinator/SKILL.md`: boundary-board invariants and lane router.
- `plugins/codex-coordinator/skills/codex-coordinator/capabilities.json`: contract-39 public behavior contract.
- `plugins/codex-coordinator/skills/codex-coordinator/scripts/coordination_state.py`: active claim list/claim/release helper, deterministic assignment and receipt classifier, routing-only failed-delivery fallback, and generated current-view renderer.
- `plugins/codex-coordinator/mission_control/`: optional manually started, read-only, single-project dashboard that reuses the state helper and refreshes only on request.
- `plugins/codex-coordinator/skills/codex-coordinator/references/`: execution, messaging, recovery, installation, maintenance, and Doctor guidance.
- `plugins/codex-coordinator/scripts/codex_coordinator_doctor.py`: manual read-only compatibility check.
- `plugins/codex-coordinator/scripts/codex_coordinator_project.py`: dry-run-first schema-2 init/deactivate/reactivate/set-ceiling/purge and legacy schema-1 migration planning.

## Project state

- `.codex/coordination/project.yaml`: committed opt-in marker.
- `.codex/coordination/active/<thread-uuid>.json`: ignored active task-owned claims.
- `.codex/coordination/pending-notices/<recipient-thread-uuid>/<record-id>.json`: compatibility path for ignored routing-only pending delivery records created only when native delivery has no visible receipt; deleted after verified receipt or recipient action.
- `.codex/coordination/CURRENT.md`: ignored, generated active-only human view; never canonical state.
- `.codex/coordination/archive/<thread-uuid>-<time>.json`: ignored compact cold receipts.
- Schema-1 task, inbox, cache, and differently shaped `CURRENT.md` records may remain as preserved ignored history but are never schema-2 authority.

## Optional observer boundary

The package includes one small `mission_control.py` server and its usage guide. It is started manually
for one explicit project, binds to localhost, reads only the public schema-2 board, and refreshes only
on request. There is no collector, background launcher, lifecycle helper, database, task control, or
private Codex integration. The larger removed implementation remains available from dated decision
records and Git history.

## Public and contributor docs

- `README.md`: current behavior, installation, and release status.
- `docs/OPERATING_GUIDE.md`: operator commands and boundaries.
- `docs/DISCOVERY.md`: when to recommend the board or a simpler path.
- `docs/codebase/2026-07-21_boundary-board-simplification_architectural_review.md`: exhaustive decision history.
- `docs/codebase/2026-07-22_claim-lifecycle-stop-guard_architectural_review.md`: stale terminal-claim diagnosis and bounded correction.
- `docs/codebase/2026-07-23_cooperative-shared-checkout_architectural_review.md`: reuse-first, advisory-path, cooperative-Git correction.
- `docs/codebase/2026-07-23_cross-harness-portability_architectural_review.md`: proposed Claude-first portable core and later Hermes/OpenClaw adapter roadmap; not a current support claim.
- `CHANGELOG.md`: chronological behavior changes.
- `PRIVACY.md`, `TERMS.md`, `SECURITY.md`: public trust boundaries.

## Tests

- `test_coordination_state.py`: task-owned records, overlap, concurrency, limits, routing-only pending delivery records, privacy, and cold receipts.
- `test_boundary_workflow.py`: fresh isolated install through init, claim, advisory overlap, release, and disable.
- `test_session_start.py`: silent opt-out, bounded hint, exact-recipient pending count, malformed markers, and no launcher.
- `test_stop_guard.py`: exact-own-claim lifecycle check, one-shot circuit breaker, privacy, linked worktree, and fail-open paths.
- `test_prompt_guard.py`: assignment identity plus matching, mismatched, delegated, ordinary, and unverifiable repository-placement cases.
- `test_native_task_fault_protocol.py`: committed native create/send with lost response, true no-receipt fallback, and no-blind-retry behavior.
- `test_doctor.py`: read-only package compatibility and reinstall-only failure.
- `test_project_lifecycle.py`: dry-run-first init, disable, migration, preservation, and purge confirmation.
- `test_package_contract.py`, `test_goal_leadership_contract.py`: architecture and guidance regression gates.
- `test_mission_control*.py`, `test_doctor_scan.py`: bounded observer behavior and optional-tool isolation from the base runtime.
- Public site, release, and hygiene tests cover distribution surfaces separately.
