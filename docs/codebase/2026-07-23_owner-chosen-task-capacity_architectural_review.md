# Owner-chosen task-capacity architectural review

> **2026-07-23 ceiling correction:** [The contract-36 capacity review](2026-07-23_five-task-user-managed-ceiling_architectural_review.md) supersedes the capless policy below. One task remains the default; five active durable tasks including the Coordinator is the project ceiling. The user may approve an exact temporary higher count or update the persistent project ceiling.

Status: accepted and implemented

Date: 2026-07-23

## Scope

This review replaces the plugin-owned normal maximum of three active tasks and hard maximum of
twelve active board records. The owner may now choose the task count, or the acting agent may choose
the smallest useful set for the goal and available host capacity.

It does not weaken assignment identity, reuse-before-create, sequential task creation, exact
repository placement, bounded record size, revision checks, path warnings, exact exclusive-action
conflicts, external-write consent, or the one-task-first default.

## Evidence checked

- `coordination_state.py` owned both count checks and exposed `defaultLimit` and `hardLimit`.
- The capability contract and Doctor repeated the fixed `three-default-twelve-hard-user-override`
  policy.
- `SKILL.md`, `references/execution.md`, the operating guide, architecture guide, discovery copy,
  website, README, and tests repeated the same count.
- The existing deterministic assignment ID and sequential readback path already prevents duplicate
  task creation without needing a capacity policy.

## Tool baseline

The repository has no separate task-capacity service or provider setting to reuse. The existing
state helper remains the only board mutation owner. No dependency or second configuration owner is
needed.

## Agent-led review

The fixed cap mixed two separate decisions: whether a new task is useful and whether a claim record
is safe. Record size, path/action counts, validation, locking, and atomic writes already bound each
record. Assignment identity and sequential native readback already protect the creation path.
Therefore task quantity can return to the owner or acting agent without removing the controls that
protect state integrity and duplicate creation.

The legacy `limitOverride` claim field and `--user-approved-over-limit` CLI flag remain accepted for
schema and caller compatibility, but they no longer affect task count. Board reports retain the
`defaultLimit` and `hardLimit` keys with `null` values so existing readers do not lose fields.

## Findings

1. The fixed count was product policy embedded in the state helper, not a safety requirement owned
   by the claim schema.
2. Removing only the marketing wording would leave runtime behavior and public claims inconsistent.
3. Removing assignment identity, sequential creation, or collision controls would be unrelated and
   unsafe; those controls remain.

## Recommended fixes

- Remove count rejection from active-record reads and claim creation.
- Report no plugin-owned normal or hard limit.
- Keep one task as the default and require every additional durable task to own a complete useful
  result.
- Let the owner select a count explicitly or let the acting agent select the smallest useful set.
- Preserve historical fixed-limit decisions in dated records and the changelog.

## Verification

The state-helper tests must prove that more than twelve valid active claims are accepted without an
override and that the report returns `null` for both legacy limit fields. Package tests must bind the
new capability contract, and the complete repository suite must pass.

## Follow-up

The OpenAI directory draft still contains the pre-change uploaded package. Replace that bundle only
during the later reviewed release update; do not submit the stale draft.
