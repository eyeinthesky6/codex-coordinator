# Stack

Codex Coordinator is a source-distributed Codex plugin. Its behavior is primarily documented as a Codex skill, with one Python hook used to restore coordination context when a task starts or resumes.

## Runtime

- OpenAI Codex with plugin, skill, and hook support.
- Git for repository identity, primary-worktree discovery, and normal source control.
- Python 3.10 or newer for the SessionStart hook, selected by the OS-native bootstrap from PATH, registered or standard installs, or Codex runtime folders.
- Python standard library only; the plugin has no runtime package dependencies.
- PowerShell on Windows and POSIX `sh` on macOS/Linux for Python discovery and an informed best-effort install when Python is absent.

## Repository formats

- Markdown for user docs, the skill, and coordination records.
- JSON for plugin, marketplace, and hook manifests.
- YAML for the packaged agent interface, GitHub automation, issue forms, and the small project marker created in enabled repositories.
- TOML for Gitleaks configuration.

## Development and automation

- `unittest` for the local test suite.
- GitHub Actions for Python 3.10 and 3.13 checks on Windows and Ubuntu.
- Gitleaks through pre-commit and CI for secret-pattern scanning.
- Dependabot for GitHub Actions updates.

## Evidence

- `plugins/codex-coordinator/.codex-plugin/plugin.json`
- `plugins/codex-coordinator/hooks/hooks.json`
- `plugins/codex-coordinator/scripts/codex_coordinator_session_start.py`
- `.github/workflows/ci.yml`
- `.pre-commit-config.yaml`
