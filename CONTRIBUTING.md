# Contributing

Thank you for helping improve Codex Coordinator.

## Before opening a change

- Search existing issues and pull requests.
- Keep changes focused on cross-task coordination. Avoid project-specific rules.
- Discuss broad behavior or protocol changes in [Ideas](https://github.com/eyeinthesky6/codex-coordinator/discussions/categories/ideas) before opening implementation work.
- Never include credentials, private task content, or a project's live `.codex/coordination/` state.
- Read the relevant files in `docs/codebase/` before changing package, protocol, hook, or test boundaries.

Documentation, reproducible bug reports, compatibility checks, and focused test improvements are welcome alongside code changes.

## Development

Use Python 3.10 or newer. Run the test suite from the repository root:

```shell
python -m unittest discover -s tests -p "test_*.py" -v
```

Optional local secret scanning is available through pre-commit:

```shell
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Pull requests

Explain the user-visible behavior, why the change is needed, and how it was tested. Keep documentation aligned with behavior and avoid unrelated cleanup.

Maintainers will prioritize security problems, regressions, and small well-evidenced fixes. A proposal may be declined when it adds project-specific policy, duplicates native Codex behavior, or expands the trusted runtime without a clear benefit.

See [GOVERNANCE.md](GOVERNANCE.md) for how decisions and project roles are handled.

By contributing, you agree that your contribution is licensed under the MIT License.
