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

`tests/test_session_start.py` checks that:

- valid current state produces a bounded restart handoff;
- malformed, duplicate, truncated, stale, or mismatched state does not grant authority;
- primary-worktree discovery works for linked worktrees and Unicode paths;
- task ownership, registration, status, and pending-command fields agree;
- hook packaging uses the expected `${PLUGIN_ROOT}` commands.

## CI matrix

GitHub Actions runs the unit suite on Python 3.10 and 3.13 on both Ubuntu and Windows. A separate job scans Git history with Gitleaks.

[TODO] Record the first public CI run URL after the GitHub remote is created.

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
- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
