# Execution and claims

Read this file completely before creating durable tasks or changing an active claim.

## Start or join work

1. Resolve the primary worktree from the first `worktree` record in `git worktree list --porcelain`. The primary worktree owns the board even when product work runs in a linked worktree.
2. Read the marker there. A disabled marker means continue normally without reading board state. An enabled marker must use schema 2 and the exact current project ID.
3. Run the state helper's `list` command before substantial writes:

   ```text
   python <installed-skill>/scripts/coordination_state.py list --project-root <primary-worktree>
   ```

4. Read only the compact active records returned by that command. Legacy schema-1 `CURRENT.md`, task files, inbox records, archives, transcripts, and rollout logs are not active input.

Generated schema-2 `CURRENT.md` is a non-authoritative, active-only view backed by these claims and atomically rebuilt after state mutations. A Coordinator may read it when invoked, but all conflict checks and mutations still use the individual claims.

## Keep task count small

One task is the default. Investigation, implementation, tests, documentation, and follow-up fixes for one coherent outcome stay in that task.

A second or third durable task is justified only when all of these are true:

- the user explicitly asked for separate task windows, decomposition, or a Coordinator;
- its goal is a substantial, complete vertical with a useful bounded outcome;
- its path and exclusive-action boundary is exact;
- it can make progress without a stream of messages;
- parallel work is likely to save more time than the extra task costs;
- the complete assignment can be placed in the native creation prompt; and
- the host can place it in the same primary checkout, current worktree, and current branch.

Do not create a durable task for one test command, a small lookup, formatting, a narrow review follow-up, a mechanical document edit, or a low-risk one-or-two-file fix. Keep that work in the current task or use a parent-owned subagent when allowed by the host.

Three active durable tasks is the default maximum. A direct user decision is required to pass `--user-approved-over-limit`; twelve is the hard limit. The flag records that authority was supplied but does not create authority by itself.

## Goal-scoped Coordinator

When the user explicitly asks one task to coordinate a goal, that task may assign the smallest useful set of two or three durable verticals. Give every task its full goal, exact paths and actions, dependencies, verification, and completion condition in the first assignment. The Coordinator stays available for that goal when the user invokes it again; it is not a permanent lead and repository enablement does not create it.

Claim the exclusive `goal-coordination` action for that Coordinator. Use its bounded claim goal as the shared goal in generated `CURRENT.md`. The Coordinator may also claim `git-integration`, but it does not need a source-path claim unless it will edit that path.

After assignment, yield normally. Do not poll task status, wait a few minutes and check again, request periodic reports, create a heartbeat, or promise automatic fan-in. Native task completion does not wake the Coordinator automatically. When invoked again, read current active state and use supported native task status or results only as needed. Combine results only then, or let each completed vertical report directly.

Short dependent checks may still use parent-owned subagents when the host supports them. This does not forbid complete durable verticals assigned by an explicit Coordinator.

## Shared checkout and Git

All coordinated task windows use the same primary checkout, current worktree, and current branch so they share the repository's untracked settings, offline runners, and local runtime context. Do not create or switch branches or worktrees. If the task-creation path would create another worktree, do not use it for coordinated work.

Name exactly one `git-integration` owner before multiple tasks write. Every other task may edit and test its claimed paths, but it does not stage, commit, push, switch branches, create worktrees, reset, restore, stash, rebase, merge, or clean. Serialize shared generated files, lockfiles, schemas, and formatter-wide output through the named owner.

## Create or update a claim

Use the exact native thread UUID. If the host does not expose an exact UUID, do not begin parallel writes; continue single-task work or report that safe board identity is unavailable.

Create revision 1 with `--expected-revision 0`:

```text
python <installed-skill>/scripts/coordination_state.py claim \
  --project-root <primary-worktree> \
  --thread-id <exact-native-thread-uuid> \
  --title <short-native-title> \
  --goal <one-bounded-goal> \
  --path <repository-relative-path> \
  --action <exclusive-action-if-any> \
  --expected-revision 0
```

For an update, pass the exact current revision. A revision mismatch means another turn changed the claim; list the board again before writing. The helper refuses an overlap and rechecks after the atomic write so two tasks cannot silently settle on conflicting boundaries.

Two path claims overlap when they are equal or when one is an ancestor of the other. Matching is case-insensitive so the same board stays safe across common Windows and macOS filesystems.

Use `.` only when the task genuinely needs the whole repository. Prefer the narrowest useful file or directory boundary. Concrete paths only: no absolute paths, traversal, drive prefixes, or globs.

Exclusive action names are short lowercase slugs. Typical examples are `goal-coordination`, `git-integration`, `release`, `deployment`, `database-migration`, `environment`, `runtime`, or `external-write`. Do not claim an action the task is not authorised to perform.

Set `--status blocked --blocked-by <thread-uuid>` only for a real dependency. A status is visibility, not a command to the other task.

Update the claim only when work starts, scope materially changes, blocked state changes, or work completes or stops. Do not write periodic progress, commentary, findings, or a heartbeat into the claim.

## Work and Git ownership

- Preserve existing dirty work and edit only claimed paths.
- Disjoint writers share the primary checkout and current branch. Serialize shared files such as lockfiles, schemas, generated indexes, and formatter-wide output.
- When more than one writer exists, one task claims `git-integration`. Other tasks do not mutate Git state.
- Direct commits and pushes remain the normal path for one owner. Use a pull request only when the user or repository policy asks for one, or independent review materially benefits from an immutable remote diff.
- Pull requests are optional; the board never requires one.
- Another active claim is not a blocker when paths and actions are disjoint.

## Complete and release

At a safe terminal boundary, move the claim out of the hot board before the task's final answer:

```text
python <installed-skill>/scripts/coordination_state.py release \
  --project-root <primary-worktree> \
  --thread-id <exact-native-thread-uuid> \
  --expected-revision <current-revision> \
  --status completed
```

Allowed final states are `completed`, `stopped`, `superseded`, and `stale-owner-confirmed`. The helper writes one compact cold receipt, then removes the active claim. It never archives or deletes the native Codex task.

The task reports its own result, changed files, checks, commit or diff when relevant, remaining risk, and blocker. No completion acknowledgement, inbox entry, full-turn ledger, transcript mirror, or permanent Coordinator summary is required.

The packaged Stop guard is a last-resort reminder, not a normal extra workflow. It reads only this task's exact active claim. If it requests a continuation, release finished work immediately. When work genuinely must remain owned across turns, retain or update only this task's claim and state that fact briefly. The guard does not inspect another task, infer completion from transcript text, or run more than once for the same stop attempt.
