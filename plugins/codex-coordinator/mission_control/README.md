# Legacy Mission Control source

This directory contains the schema-1 Mission Control prototype preserved during the boundary-board realignment. It is not a supported schema-2 component.

Do not run it against a schema-2 project. It still depends on legacy `CURRENT.md`, inbox, heartbeat, private native-state, Doctor-repair, and semantic-review behavior that the schema-2 core removed.

Nothing in SessionStart, Doctor, the state helper, lifecycle helper, capability contract, or package prompts imports or starts this code. It has no current product authority.

Mission Control will be handled in a separate reviewed decision:

1. rebuild it as a separately installed, manually started, read-only observer over only the public schema-2 board; or
2. remove it while retaining its design and security history in Git.

A retained observer may not inspect private Codex SQLite or rollout data, repair files, call a model, write findings, create or manage tasks, monitor providers or schedules, or start from SessionStart.
