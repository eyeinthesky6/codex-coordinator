# Optional Mission Control release boundary

## Scope

Make the live Product Hunt promise of a local Mission Control truthful without restoring the v0.3
collector, monitoring loops, task controls, transcript reads, Doctor repair, or orchestration cost.
Also close the live assignment-identity bug where a hand-written ID could pass after matching only
the required text shape.

## Evidence Checked

- v0.3 Mission Control source and tests at tag `v0.3.0`;
- current schema-2 state helper, hooks, capability contract, skill guidance, and package tests;
- the live Product Hunt page on 24 July 2026;
- current working-tree and release diff from `v0.4.0`.

## Tool Baseline

The canonical schema-2 helper already validates the enabled marker, bounded active claims, exact
exclusive-action conflicts, path warnings, and deterministic assignment identity. Reusing it avoids
a second state parser or task authority.

## Agent-Led Review

The v0.3 observer was unsuitable to restore: its collector, server, launchers, settings, all-project
view, and task-facing controls were coupled to the removed orchestration system. The remaining user
job is narrower: see the active tasks and real conflicts for one project without opening every task.

The smallest supported path is one manually started localhost page that calls the current helper on
page load and renders its existing result. It has no automatic refresh and no write endpoint. The
failure path is a clear unavailable page or command error when the project is disabled or invalid.

For assignment identity, format validation alone was insufficient. The existing helper already owns
the deterministic calculation from project ID, exact active goal-Coordinator claim instance, and
lane key. The prompt guard now reuses that owner and compares the expected value before native goal
binding.

## Findings

1. Restoring the v0.3 runtime would reintroduce the largest removed subsystem and its hot-path
   coupling.
2. A manual single-project view satisfies the current public promise without monitoring or task
   authority.
3. Assignment-ID shape checks did not prove provenance; a fabricated 32-hex value could pass.
4. The current release diff adds multiple user-visible capabilities and warrants `v0.5.0`, not a
   patch release under the already published `v0.4.0` identity.

## Recommended Fixes

- Ship `mission_control/mission_control.py` as optional package content only.
- Bind only to `127.0.0.1`; require an explicit project root; refresh only on page reload.
- Reuse `coordination_state.list_board`; add no database, cache, scanner, API client, or dependency.
- Require `Lane-Key`, plain routing identities, and the enabled active goal Coordinator for
  `GOAL_ASSIGNMENT` and `RESULT_READY`; recompute and compare the assignment ID.
- Keep the old collector, automatic refresh, lifecycle launchers, settings, Doctor integration, and
  task controls historical.

## Verification

- Focused prompt-guard tests include a well-formed fabricated-ID rejection.
- Mission Control tests exercise an initialized active board and assert the rendered page has no
  polling or task/message controls.
- Full package, lifecycle, public-site, and clean-install checks remain release gates.

## Follow-Up

Treat requests for multi-project scanning, automatic refresh, background startup, task controls, or
private Codex state as new architecture proposals. They are not incremental Mission Control UI work.
