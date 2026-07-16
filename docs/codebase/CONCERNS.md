# Concerns and launch gates

## Current launch gates

- The repository is staged on a private GitHub remote; it has no public history, tag, or release artifact yet.
- The initial remote CI matrix passed, and the GitHub support funnel is configured.
- Branch protection, secret scanning, push protection, and private vulnerability reporting remain deferred until public-repository features are available.
- A full Codex Security scan is deferred while local resources are busy. It is an additional project safety gate, not a GitHub or licensing requirement.

These are external or finalization gates, not evidence of a code defect.

## Product boundaries to preserve

- Coordination records are local to one checkout and do not synchronize between machines.
- The hook is helpful restart context, not proof of current ownership.
- Users must review and trust the hook; changed hooks may be skipped until reviewed again.
- The protocol depends on Markdown and small YAML records staying compatible with the documented schemas.
- Git worktrees isolate files, while Coordinator tracks responsibility. Neither replaces the other.

## Maintenance risks

- Codex plugin and hook contracts may evolve; package metadata and installation instructions need checking before each release.
- New protocol fields can create compatibility drift between the skill, hook parser, examples, and tests.
- Expanding the hook with dependencies, writes, or network access would materially increase trust and supply-chain risk.
- Public support reports may accidentally include private task content or local coordination state; issue forms and support docs must continue warning against that.

## Evidence

- `README.md`
- `SECURITY.md`
- `SUPPORT.md`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `tests/`
- `.github/`
