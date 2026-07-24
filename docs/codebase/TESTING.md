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
- equal, ancestor, case-equivalent, and repository-wide paths produce advisory warnings without blocking either task;
- exact exclusive actions still collide, while legacy `git-integration` is advisory;
- the board defaults to five active durable tasks including the Coordinator, stops an unapproved sixth claim, and accepts only explicit user-approved higher capacity;
- an optional project ceiling is validated, while a missing field remains compatible and defaults to five;
- revisions require exact integers and the deprecated compatibility override still requires an actual boolean;
- unknown/transcript fields, unsafe paths, invalid identities, and oversized records fail;
- terminal claims leave the hot board and create compact receipts;
- concurrent path-overlapping writers remain visible, while concurrent exact exclusive actions leave one owner.
- deterministic assignment IDs remain stable for one Coordinator claim instance and lane key;
- prompt-time assignment verification recomputes that identity and rejects a well-formed fabricated ID;
- optional Mission Control renders one enabled active board without polling, task controls, messages, or transcript access;
- invalid lane keys or Coordinator identities fail without creating state;
- every native mutation receipt outcome resolves to attempt once, use one exact receipt, stop on duplicates, or stop unknown without retry.
- a true no-receipt assignment or terminal return creates one idempotent routing-only pending delivery record for the exact recipient, and verified receipt or recipient action deletes it without an archive.

`test_session_start.py` proves:

- absent and disabled markers are silent;
- enabled schema 2 emits a short hint only;
- only the exact current task's pending-delivery filenames are counted, and no record body is read;
- schema 1, duplicate keys, incompatible access, and oversized markers fail closed;
- the hook never launches a process, Python installer, browser, or observer;
- the registered timeout is five seconds and bootstrap scripts are absent.

`test_stop_guard.py` proves:

- disabled, absent, unowned, blocked, and circuit-breaker paths are silent;
- only the exact active `session_id` claim produces one bounded continuation;
- transcript and assistant-message input is ignored and never returned;
- malformed claims fail open rather than wedging the task;
- linked worktrees resolve the primary board;
- Stop registration is matcher-free, direct, and capped at five seconds.

`test_prompt_guard.py` proves:

- compact and documented `GOAL_ASSIGNMENT` and `RESULT_READY` communication shapes are detected;
- inter-agent task communication rejects the retired header, schema/revision annotations, assignment fields, permission grants, unrelated status, and project mismatch while preserving the non-executable factual form;
- durable assignments require `Native-Goal: REQUIRED` and one bounded native goal objective;
- a valid durable assignment receives the system-level `get_goal` / `create_goal` binding instruction before repository work;
- the full bounded prompt is checked rather than only its first 8 KB;
- each actionable communication requires one valid assignment ID and one verifiable absolute local repository;
- wrong or missing repository placement blocks before goal activation;
- duplicated fields are blocked, while matching communication and ordinary prompts remain silent.

`test_native_task_fault_protocol.py` uses a fake native host that commits a mutation and then returns `No handler registered`. It proves:

- a committed task creation with a lost response is found by the exact assignment ID and is not created twice;
- a committed terminal `RESULT_READY` with a lost response is found and is not resent;
- an ambiguous mutation with no visible receipt stops instead of retrying and leaves one idempotent routing-only recovery fact.

This is deterministic host-boundary fault injection. A real Codex-host transactional guarantee remains outside the plugin because the native API exposes no idempotency key or authoritative mutation receipt.

`test_handover_properties.py`, when its separate test dependency is installed, generates claim, update, overlap, stale-revision, view-rebuild, release, and observation sequences. It also generates invalid revision and approval types so Python coercion cannot create authority.

`test_doctor.py` proves:

- the packaged manifest, contract-38 capability file, skill links, state and project-lifecycle helpers, all three lifecycle hooks, and native-goal durable-task/dependent-subagent guidance are compatible;
- malformed or drifted packages report `broken` and `update_or_reinstall`;
- compact output omits detailed findings and local paths;
- legacy `--apply` and separate repair targets write nothing;
- no scanner, rollback, copy, process, diagram, project, or private-data path exists.

`test_project_lifecycle.py` proves:

- new-project init is dry-run-first, creates only the bounded board files, and rejects ambiguous existing state;
- schema-2 deactivation/reactivation creates no native lifecycle action;
- project ceiling changes are dry-run-first, marker-only, idempotent, and preserve active claims and history;
- state and cold history survive deactivation;
- legacy schema 1 can be disabled but cannot be reactivated without migration;
- purge requires exact project confirmation;
- no global project registry or drive scan exists;
- no new Coordinator, pin, heartbeat, or observer action is created.

`test_boundary_workflow.py` copies the package to an isolated location and proves one complete workflow: Doctor, new-project init, SessionStart hint, empty board, disjoint claims, advisory overlap, compact releases, and clean disable with no legacy task state.

## Architecture regressions

Package and leadership tests enforce the one-task default, a five-task normal ceiling including the Coordinator, direct-user authority for exact temporary or persistent increases, a user-invoked native-goal Coordinator, a one-time exact-Coordinator pin after goal binding and claim success, user-controlled unpinning, no worker or enablement pinning, native Goal mode for every durable worker, no durable windows for short work, completed-related-task reuse before create, deterministic lane IDs, goal-Coordinator-only worker creation, an immediate native capacity check before each sequential create, exact placement and distinct-title readback, one receipt readback without blind retry after an ambiguous native mutation, exact-task completion or attention waits, one terminal result fallback without progress polling, pull-first passive visibility, an exact-recipient action gate, no routine update or Coordinator-relay messages, bounded same-task follow-up decisions, cleanup of an explicitly requested temporary native thread heartbeat, complete durable verticals in one shared checkout, parent-owned subagents for short dependent checks, cooperative exact-file Git commits, advisory path overlap, narrow exclusive-action locks, optional PR policy, sparse inter-agent task communication, evidence-based stale recovery, no general inbox or transcript store, no provider or project-schedule monitoring, no Python bootstrap, and no optional-tool reachability.

Legacy-observer and Doctor-scanner tests no longer validate their old behavior. They now prove those components are absent from or isolated outside the schema-2 base runtime. A future optional observer needs a separate package and its own tests before it can be supported.

## Performance evidence

Before release, measure at least:

- disabled SessionStart;
- enabled SessionStart;
- enabled Stop with no own claim and with one exact active claim;
- ordinary and matching-communication UserPromptSubmit;
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
