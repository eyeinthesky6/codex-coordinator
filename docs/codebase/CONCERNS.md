# Concerns and launch gates

## Current release gates

- The repository is public. A release candidate is not supported until it passes protected CI, is merged, tagged, published, and verified from a clean checkout of that exact tag.
- Mission Control is source-installed from an exact tag. It is not bundled into the Codex plugin cache and users must restart its local process after changing source versions.
- GitHub branch protection, required CI, secret scanning, push protection, private vulnerability reporting, and CodeQL are enabled. Provider controls must still be read back for each release.
- Immutable future releases are not enabled; tags and GitHub Release state therefore remain part of the maintainer's release discipline.

These are release and provider conditions, not evidence of an application-code defect.

## Product boundaries to preserve

- Coordination records are local to one checkout and do not synchronize between machines.
- Mission Control is a single-machine localhost observer. It infers live state from bounded local receipts and never becomes a cross-machine task service.
- The hook is helpful restart context, not proof of current ownership.
- Users must review and trust the hook; changed hooks may be skipped until reviewed again.
- The protocol depends on Markdown and small YAML records staying compatible with the documented schemas.
- Git worktrees isolate files, while Coordinator tracks responsibility. Neither replaces the other.

## Maintenance risks

- Codex plugin and hook contracts may evolve; package metadata and installation instructions need checking before each release.
- New protocol fields can create compatibility drift between the skill, hook parser, examples, and tests.
- Expanding the hook with dependencies, writes, or network access would materially increase trust and supply-chain risk.
- Public support reports may accidentally include private task content or local coordination state; issue forms and support docs must continue warning against that.
- Mission Control depends on local Codex receipt and state-database shapes that may evolve; collected fail-safe tests and real-browser UAT must be rerun against supported Codex updates.

## Evidence

- `README.md`
- `SECURITY.md`
- `SUPPORT.md`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `apps/mission_control/`
- `tests/`
- `.github/`
