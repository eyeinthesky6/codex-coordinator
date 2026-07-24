# Native-goal binding architectural review

> Goal-supervision follow-up (2026-07-23): [the goal-supervision review](2026-07-23_goal-supervision_architectural_review.md) keeps native Goal mode as authority and makes the goal Coordinator wait on exact completion or attention events. A worker still sends one terminal `RESULT_READY`; an explicitly unattended goal may add one temporary native thread heartbeat with mandatory cleanup.

## Decision

Every durable Codex Coordinator lane must use native Codex Goal mode. A prose `GOAL_ASSIGNMENT` is routing and boundary metadata, not a substitute for `create_goal`.

Work that is too short or mechanical for a persisted native goal stays in the current task or a parent-owned helper. It does not receive a durable task window.

## Symptom

The Coordinator was opening tasks with prompts that described “your goal,” but the receiving task did not activate the native goal lifecycle. The task could therefore treat the assignment as one ordinary execution turn, return early, and leave the larger vertical unfinished. At the same time, short commands and reviews could pass the prose-only “complete vertical” judgment and create unnecessary windows.

Reuse was also too narrow: the contract expected a reusable recipient to have a matching active claim. A completed related task normally has no active claim, so this rule favoured new task creation over useful context reuse.

## Native capability checked

The current Codex manual describes goals as a stable feature providing persisted goals and automatic continuation. It says the goal text becomes the task's first prompt and completion criteria, and recommends an outcome, constraints, and verification. The callable native interface in this host exposes `get_goal`, `create_goal`, and `update_goal` for the current task.

A Coordinator cannot directly call `create_goal` inside another task. The receiving task must do that itself. A valid assignment therefore needs a system-level instruction at prompt submission, not merely another task's conversational claim that text is a goal.

## Corrected flow

1. The user explicitly appoints a Coordinator for a multi-step shared goal.
2. The Coordinator binds its own shared objective to native Goal mode when no matching goal is active.
3. It reuses a related task before creating another. Visible context is a preflight; the recipient's `get_goal` call is authoritative.
4. Every durable creation prompt or reused-task message is a `GOAL_ASSIGNMENT` containing the assignment ID, exact repository, `Native-Goal: REQUIRED`, and one measurable `Goal:`.
5. The prompt hook validates those fields and adds a short system instruction requiring `get_goal` and safe `create_goal` binding before repository action.
6. A recipient with no unfinished goal creates the exact goal. A recipient with the same active goal continues. A different unfinished goal is never overwritten.
7. Native Goal mode keeps the task working across continuation turns. The worker completes outcome and verification before marking the native goal complete, releasing its board claim, and sending one terminal `RESULT_READY`.

## Retained boundaries

- Native Codex remains the execution, goal, message, result, and transcript authority.
- Coordinator state stores no goal transcript, reasoning, progress diary, or tool output.
- There is no heartbeat, polling loop, acknowledgement chain, resident Coordinator, or automatic short-task fan-out.
- The goal-binding hook does not call tools, inspect another task, read transcripts, or create state.
- A different unfinished native goal blocks reuse instead of being replaced.
- Goal mode grants no extra filesystem, external-write, release, deployment, environment, or provider authority.
- If native goal tools are unavailable to a recipient, no durable worker is created for that lane; work remains in one task instead of falling back to prose-only goals.

## Verification

- Valid `GOAL_ASSIGNMENT` receives a system instruction naming `get_goal` and `create_goal`.
- Missing or duplicate native-goal fields are blocked before work.
- `RESULT_READY` keeps its existing silent repository and assignment-ID guard.
- Package tests require native-goal binding for the Coordinator and durable workers.
- A live enabled-project trial must still prove that the recipient actually calls `create_goal`, automatically continues until the vertical is complete, and returns once without polling.

## Remaining host boundary

The plugin can validate the assignment and issue a system instruction, but it cannot invoke `create_goal` remotely in another task or query that task's private goal tool directly. The receiving Codex task owns that native mutation. If the host later exposes goal creation as part of `create_thread` or `send_message_to_thread`, the plugin should use that native parameter and remove the prompt-level bridge rather than maintaining a second goal system.
