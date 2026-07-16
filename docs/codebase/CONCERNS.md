# Concerns and launch gates

## Current launch gates

- The repository has no public remote, public commit history, tags, or release artifact yet.
- GitHub-side protections and community routes cannot be verified until the repository is hosted.
- The first remote CI run has not happened.
- The scheduled full Codex Security scan must finish before public launch.

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
