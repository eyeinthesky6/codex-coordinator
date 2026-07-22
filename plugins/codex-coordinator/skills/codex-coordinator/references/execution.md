# Execution and claims

Read this file completely before creating durable tasks or changing an active claim.

## Start or join work

1. Resolve the primary worktree from the first `worktree` record in `git worktree list --porcelain`. The primary worktree owns the board even when product work runs in a linked worktree.
2. Read the marker there. A disabled marker means continue normally without reading board state. An enabled marker must use schema 2 and the exact current project ID.
3. Run the state helper's `list` command before substantial writes:

   ```text
   python <installed-skill>/scripts/coordination_state.py list --project-root <primary-worktree>
   ```

4. Read only the compact active records returned by that command. Do not read `CURRENT.md`, legacy task files, inbox records, archives, transcripts, or rollout logs.

## Keep task count small

One task is the default. Investigation, implementation, tests, documentation, and follow-up fixes for one coherent outcome stay in that task.

A second or third durable task is justified only when all of these are true:

- its goal is substantial and independently useful;
- its path and exclusive-action boundary is exact;
- it can make progress without a stream of messages;
- parallel work is likely to save more time than the extra task costs;
- the complete assignment can be placed in the native creation prompt.

Do not create a durable task for one test command, a small lookup, formatting, a narrow review follow-up, a mechanical document edit, or a low-risk one-or-two-file fix. Keep that work in the current task or use a parent-owned subagent when allowed by the host.

Three active durable tasks is the default maximum. A direct user decision is required to pass `--user-approved-over-limit`; twelve is the hard limit. The flag records that authority was supplied but does not create authority by itself.

When the user explicitly asks one task to split a goal, that task may act as a temporary lead: create the smallest useful set of native tasks, give each a complete first-turn assignment, and combine their completed results when requested. Do not pin it, retain it after the goal, create a heartbeat, or turn repository enablement into permanent management.

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

Exclusive action names are short lowercase slugs. Typical examples are `git-integration`, `release`, `deployment`, `database-migration`, `environment`, `runtime`, or `external-write`. Do not claim an action the task is not authorised to perform.

Set `--status blocked --blocked-by <thread-uuid>` only for a real dependency. A status is visibility, not a command to the other task.

## Work and Git ownership

- Preserve existing dirty work and edit only claimed paths.
- Disjoint writers may share one checkout. Serialize shared files such as lockfiles, schemas, generated indexes, and formatter-wide output.
- When more than one writer exists, one task claims `git-integration`. Other tasks do not switch branches, stage broad changes, commit, reset, restore, stash, rebase, merge, or clean unless the user separately assigns that action.
- Direct commits and pushes remain the normal path for one owner. Use a pull request only when the user or repository policy asks for one, or independent review materially benefits from an immutable remote diff.
- Pull requests are optional; the board never requires one.
- Another active claim is not a blocker when paths and actions are disjoint.

## Complete and release

At a safe terminal boundary, move the claim out of the hot board:

```text
python <installed-skill>/scripts/coordination_state.py release \
  --project-root <primary-worktree> \
  --thread-id <exact-native-thread-uuid> \
  --expected-revision <current-revision> \
  --status completed
```

Allowed final states are `completed`, `stopped`, `superseded`, and `stale-owner-confirmed`. The helper writes one compact cold receipt, then removes the active claim. It never archives or deletes the native Codex task.

The task reports its own result, changed files, checks, commit or diff when relevant, remaining risk, and blocker. No completion acknowledgement, full-turn ledger, or permanent Coordinator summary is required.
