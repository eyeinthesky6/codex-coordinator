# Conventions

## Product rules

- Coordinate only when work is meaningfully parallel, overlapping, or crossing Codex tasks.
- Keep small isolated work free of coordination ceremony.
- Use existing Codex task tools for execution and messaging; the plugin adds protocol and durable state.
- Treat repository identity, exact native task identity, and current ownership as required routing evidence. Schema 2 has no epoch or registered-session ledger.
- Preserve an explicit opt-out and never silently re-enable an opted-out repository.

## Python rules

- Use the standard library and Python 3.10-compatible syntax.
- Keep file reads and output bounded.
- Keep the SessionStart hook read-only and network-free.
- Keep the Stop hook read-only, network-free, exact-own-claim-only, transcript-free, and one-shot.
- Fail closed on authority: malformed or incomplete state may produce a warning, but must not grant ownership.
- Prefer small validation helpers and test externally visible output.

## Documentation and package rules

- Keep behavior in the top-level skill and its focused references; do not duplicate the full protocol across files.
- Use relative package paths and keep resolved assets, hooks, scripts, and skill references inside the plugin directory.
- Keep root and distributed-plugin licenses identical.
- Update the changelog for release-visible changes.
- Use plain language and state limits explicitly.

## Tests and changes

- Name tests `test_<behavior>` and run them with `unittest` discovery.
- Add a regression test when behavior, parsing, routing, or packaging changes.
- Keep pull requests focused and explain user-visible impact plus validation.

## Evidence

- `AGENTS.md`
- `CONTRIBUTING.md`
- `plugins/codex-coordinator/skills/codex-coordinator/SKILL.md`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `tests/`
