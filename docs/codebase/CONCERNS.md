# Concerns and launch gates

## Current release gates

- The repository is public. A release candidate is not supported until it passes protected CI, is merged, tagged, published, and verified from a clean checkout of that exact tag.
- Schema 2 is the `v0.4.0` release contract, while maintainer projects remain disabled until deliberately re-enabled. Passing source tests does not by itself prove an installed or re-enabled workflow.
- The base package no longer contains Mission Control. Any future observer is a separate product decision and cannot be restored by copying the schema-1 runtime forward.
- GitHub branch protection, required CI, secret scanning, push protection, private vulnerability reporting, and CodeQL are enabled. Provider controls must still be read back for each release.
- Immutable future releases are not enabled; tags and GitHub Release state therefore remain part of the maintainer's release discipline.

These are release and provider conditions, not evidence of an application-code defect.

## Product boundaries to preserve

- Coordination records are local to the primary checkout and do not synchronize between machines.
- Coordinated task windows stay in that shared checkout and current branch. The product does not create worktrees; one task owns Git integration.
- The SessionStart hook is a bounded marker hint, not proof of current ownership.
- Users must review and trust the hook; changed hooks may be skipped until reviewed again.
- The protocol depends on small YAML and JSON records staying compatible with the documented schemas.
- Git worktrees intentionally isolate files, but this Coordinator mode deliberately keeps assigned lanes in the shared checkout so they retain local untracked settings and offline runners.
- Native Codex remains the only transcript and task-lifecycle authority.
- The Stop guard covers a task that reaches its normal turn boundary with an unreleased active claim. Codex exposes no app-archive hook, so an abrupt UI archive still requires exact on-demand stale-owner evidence.

## Maintenance risks

- Codex plugin and hook contracts may evolve; package metadata and installation instructions need checking before each release.
- New protocol fields can create compatibility drift between the skill, hook parser, examples, and tests.
- Expanding either hook with dependencies, network access, transcript reads, board-wide scans, or native-history reads would materially increase trust and supply-chain risk.
- A blocking Stop continuation is a host integration risk. Keep it one-shot through `stop_hook_active`, under five seconds, and fail open on every malformed or unavailable state path.
- Public support reports may accidentally include private task content or local coordination state; issue forms and support docs must continue warning against that.
- Schema-1 migration must remain dry-run-first, preserve old records, create no inferred claims, and leave projects disabled.
- Active-claim limits and record-size bounds protect the hot path; raising them or scanning cold history would reintroduce the original slowdown.
- A future observer could recreate private-Codex coupling or a second task authority unless it is separately packaged and limited to the public board.

## Evidence

- `README.md`
- `SECURITY.md`
- `SUPPORT.md`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `plugins/codex-coordinator/scripts/codex_coordinator_stop_guard.py`
- `plugins/codex-coordinator/skills/codex-coordinator/scripts/coordination_state.py`
- `docs/codebase/2026-07-21_boundary-board-simplification_architectural_review.md`
- `docs/codebase/2026-07-22_claim-lifecycle-stop-guard_architectural_review.md`
- `tests/`
- `.github/`
