# Legacy Mission Control compatibility source

The source-checkout launchers in this directory target the schema-1 Mission Control prototype. They are retained only as migration history and are not supported for schema 2.

Do not start them against a schema-2 project. See the [packaged legacy notice](../../plugins/codex-coordinator/mission_control/README.md) and the [boundary-board decision](../../docs/codebase/2026-07-21_boundary-board-simplification_architectural_review.md).

The schema-2 base plugin starts no process or browser and has no Mission Control lifecycle. Any future observer requires a separate optional package and review.
