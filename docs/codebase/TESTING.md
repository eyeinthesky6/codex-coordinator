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

- the packaged manifest, schema-20 contract, skill links, state helper, and hook are compatible;
- malformed or drifted packages report `broken` and `update_or_reinstall`;
- compact output omits detailed findings and local paths;
- legacy `--apply` and separate repair targets write nothing;
- no scanner, rollback, copy, process, diagram, project, or private-data path exists.

`test_uninstall.py` proves:

- schema-2 deactivation/reactivation creates no native lifecycle action;
- state and cold history survive deactivation;
- legacy schema 1 can be disabled but cannot be reactivated without migration;
- purge requires exact project confirmation;
- global planning uses only verified explicit roots;
- no new Coordinator, pin, heartbeat, or Mission Control action is created.

## Architecture regressions

Package and leadership tests enforce the one-task default, explicit temporary lead, small capability contract, optional PR policy, sparse non-executable messaging, evidence-based stale recovery, no transcript store, no provider/schedule monitoring, no Python bootstrap, and no optional-tool reachability.

Legacy Mission Control and Doctor-scanner tests no longer validate their old behavior. They now prove those components are outside the schema-2 base runtime. A future optional observer needs a separate package and its own tests before it can be supported.

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
