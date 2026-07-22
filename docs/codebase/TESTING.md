# Testing

## Main command

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

The runtime uses only the Python standard library. Optional property tests may skip when their separate development dependency is absent.

## Core acceptance

`test_coordination_state.py` proves:

- an empty enabled board has fixed small output;
- disabled projects do not read corrupt historical state;
- one exact task owns one exact filename;
- expected revisions prevent stale updates;
- disjoint claims proceed without a central owner or message;
- equal, ancestor, case-equivalent, and repository-wide paths collide;
- exact exclusive actions collide;
- three is the default task limit and twelve is hard;
- unknown/transcript fields, unsafe paths, invalid identities, and oversized records fail;
- terminal claims leave the hot board and create compact receipts;
- concurrent conflicting writers leave exactly one owner.

`test_session_start.py` proves:

- absent and disabled markers are silent;
- enabled schema 2 emits a short hint only;
- schema 1, duplicate keys, incompatible access, and oversized markers fail closed;
- the hook never launches a process, Python installer, browser, or Mission Control;
- the registered timeout is five seconds and bootstrap scripts are absent.

`test_doctor.py` proves:

- the packaged manifest, schema-22 contract, skill links, state and project-lifecycle helpers, and hook are compatible;
- malformed or drifted packages report `broken` and `update_or_reinstall`;
- compact output omits detailed findings and local paths;
- legacy `--apply` and separate repair targets write nothing;
- no scanner, rollback, copy, process, diagram, project, or private-data path exists.

`test_project_lifecycle.py` proves:

- new-project init is dry-run-first, creates only the bounded board files, and rejects ambiguous existing state;
- schema-2 deactivation/reactivation creates no native lifecycle action;
- state and cold history survive deactivation;
- legacy schema 1 can be disabled but cannot be reactivated without migration;
- purge requires exact project confirmation;
- no global project registry or drive scan exists;
- no new Coordinator, pin, heartbeat, or Mission Control action is created.

`test_boundary_workflow.py` copies the package to an isolated location and proves one complete workflow: Doctor, new-project init, SessionStart hint, empty board, disjoint claims, overlap rejection, compact releases, and clean disable with no legacy task state.

## Architecture regressions

Package and leadership tests enforce the one-task default, explicit temporary lead, small capability contract, optional PR policy, sparse non-executable messaging, evidence-based stale recovery, no transcript store, no provider/schedule monitoring, no Python bootstrap, and no optional-tool reachability.

Mission Control and Doctor-scanner tests no longer validate their old behavior. They now prove those components are absent from or isolated outside the schema-2 base runtime. A future optional observer needs a separate package and its own tests before it can be supported.

## Performance evidence

Before release, measure at least:

- disabled SessionStart;
- enabled SessionStart;
- empty `list`;
- three-record `list`;
- one claim and release;
- output and record sizes;
- runtime source and guidance line-count reductions against the decision-record baseline.

No ordinary operation may scale with legacy task, inbox, archive, transcript, rollout, provider, schedule, or PR history.

## Other checks

- Parse changed JSON with Python.
- Compile changed Python with `python -m py_compile` or the Doctor syntax checks.
- Run `git diff --check`.
- Verify links and public site assets.
- Confirm no live project state, private paths, credentials, generated caches, or audit artifacts enter the package.
- Check Git author and committer identity before commit.
