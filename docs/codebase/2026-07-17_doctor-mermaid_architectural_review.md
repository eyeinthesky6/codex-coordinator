# Doctor Mermaid architectural review

> **Historical and superseded:** this records the schema-1 Doctor/diagram decision. Schema 2 removed self-repair, project scanning, and Mermaid output; current failure handling is normal plugin update or reinstall. See the [boundary-board review](2026-07-21_boundary-board-simplification_architectural_review.md).

## Scope

Add a visual diagnostic to Coordinator Doctor without changing its repair authority, project-state authority, runtime dependencies, or existing JSON contract.

## Evidence Checked

- `plugins/codex-coordinator/scripts/codex_coordinator_doctor.py`
- `plugins/codex-coordinator/skills/codex-coordinator/capabilities.json`
- `plugins/codex-coordinator/skills/codex-coordinator/references/doctor.md`
- `tests/test_doctor.py`
- `tests/test_package_contract.py`
- `docs/codebase/ARCHITECTURE.md`

## Tool Baseline

Doctor already calculates file drift, missing targets, repairs, capability checks, Markdown-link checks, Python syntax, and a bounded SessionStart smoke result. Mermaid can display those facts but cannot discover them. Adding the Mermaid CLI, Graphviz, or another renderer to Doctor would weaken the plugin's standard-library-only runtime and is unnecessary because Codex and GitHub can render Mermaid text.

## Agent-Led Review

The success path remains source validation, managed-file comparison, optional atomic repair, installed-runtime validation, JSON report, and exit status. The new path projects that completed report into an atomic `.mmd` file only when `--mermaid-out` is supplied. An early source or installation error can still produce a red error diagram, but the exact cause remains only in JSON so the diagram does not copy local paths or sensitive diagnostic text.

## Findings

1. Mermaid is useful for locating a failed branch quickly, not for proving correctness.
2. Optional output avoids creating permanent artifacts during quiet scheduled Doctor runs.
3. Managed relative paths are sufficient for useful file nodes and avoid leaking machine-specific source or installation paths.
4. The existing atomic writer is the correct owner for the new artifact; a second file-writing path is unnecessary.

## Recommended Fixes

- Add `--mermaid-out` as an optional CLI path.
- Generate Mermaid only from Doctor's completed structured report.
- Keep JSON, exit codes, hashes, syntax validation, and smoke execution authoritative.
- Cover drift, missing-file, check, escaping, and CLI-write behavior with focused tests.

## Verification

- `python -m py_compile plugins/codex-coordinator/scripts/codex_coordinator_doctor.py`: passed.
- `ruff check plugins/codex-coordinator/scripts/codex_coordinator_doctor.py tests/test_doctor.py`: passed.
- `python -m unittest discover -s tests -p "test_doctor.py" -v`: 13 tests passed.
- `python -m unittest discover -s tests -p "test_*.py" -v`: 102 tests passed.
- A real `--apply --mermaid-out` upgraded the installed capability contract to version 4 and produced an `UPDATED` map.
- A following `--check --mermaid-out` reported `current`, zero drift, six passed installation checks, and produced a `CURRENT` map containing no machine-specific paths in node labels.

## Follow-Up

If Doctor later gains an executable project-state scanner, its verified project findings can be added as a separate diagram lane. Do not parse arbitrary task prose into graph edges or treat visual proximity as evidence of a conflict.
