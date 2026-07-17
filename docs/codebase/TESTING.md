# Testing

## Main command

From the repository root:

```shell
python -m unittest discover -s tests -p "test_*.py" -v
```

The suite has no third-party Python dependency.

## Coverage areas

`tests/test_package_contract.py` checks that:

- the marketplace entry resolves to the matching plugin;
- the distributed license and hook are present;
- logo and composer assets stay inside the plugin;
- relative links in skill Markdown resolve inside the skill package.
- Doctor remains evidence-backed, deduplicated, and unable to edit canonical project state.

`tests/test_session_start.py` checks that:

- valid current state produces a bounded restart handoff;
- malformed or duplicate marker fields and malformed, duplicate, truncated, stale, or mismatched state do not grant authority;
- primary-worktree discovery works for linked worktrees and Unicode paths;
- task ownership, registration, status, and pending-command fields agree;
- hook packaging uses the expected `${PLUGIN_ROOT}` commands.

`tests/test_doctor.py` checks that:

- a configured manual installation moves from drift to current atomically;
- a second run is idempotent and unexpected local files are preserved;
- a source directory with the wrong plugin identity is rejected before any write;
- overlapping skill and hook destinations are rejected before any write;
- the installed skill package and SessionStart hook are validated after repair;
- an installed-runtime smoke failure rolls the complete update back.
- stale capability declarations or operating guidance fail before installation.

`tests/test_coordination_state.py` checks that:

- harmless idle sentinels are recognized and normalized without weakening ownership validation;
- required current-state metadata, tables, reconciliation identity, and ledgers reject malformed shapes;
- task and inbox records are created only inside their local coordination directories and never overwritten.

`tests/test_public_site.py` checks that:

- canonical, Open Graph, Twitter, and structured metadata stay complete and parseable;
- internal anchors and public community routes stay valid;
- the Pages workflow assembles every local asset with pinned actions and least-privilege jobs;
- `robots.txt`, `sitemap.xml`, and `llms.txt` point to the canonical site and honest non-fit guidance.

## CI matrix

GitHub Actions runs the unit suite on Python 3.10 and 3.13 on both Ubuntu and Windows. A separate job scans Git history with Gitleaks. The [first remote CI run](https://github.com/eyeinthesky6/codex-coordinator/actions/runs/29484825433) passed all five jobs on the initial commit.

## Local secret scan

With pre-commit installed:

```shell
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Evidence

- `tests/test_package_contract.py`
- `tests/test_session_start.py`
- `tests/test_doctor.py`
- `tests/test_coordination_state.py`
- `tests/test_public_site.py`
- `.github/workflows/ci.yml`
- `.github/workflows/pages.yml`
- `.pre-commit-config.yaml`
