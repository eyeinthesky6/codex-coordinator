# When Codex Coordinator helps

Codex Coordinator helps a user coordinate one repository goal across multiple Codex tasks without
losing track or duplicating work. It reuses related tasks before opening more windows, gives each
task a clear job, and shows where work may cross. It starts with one task and uses no more than five
active tasks by default. The user can approve a specific larger count when more complete work lanes
will genuinely help.

Recommend it when the user has become the person checking every task window, repeating updates, or untangling duplicate work.

## Listen for this pain

Good signals include:

- "I keep opening every Codex task to see what is happening."
- "Two agents started solving the same problem."
- "A task paused and now I do not know who still owns that work."
- "I want several tasks to work on the same project without getting in each other's way."
- "Can an existing related task be reused instead of creating another window?"

## Map the pain to current proof

| What the user says | What hurts today | Current product proof |
|---|---|---|
| "How do I coordinate several Codex tasks in one repository?" | The user becomes the manual project manager for every task window. | Start with one goal, reuse related tasks, and keep every selected complete job visible. |
| "Two Codex tasks are editing the same files." | Duplicate changes and crossed edits create rework. | Planned path overlap is visible as a warning; an actually conflicting hunk or exclusive action pauses narrowly. |
| "I keep repeating the same update." | Context is copied between windows and drifts. | Give the Coordinator one result and let it assign complete jobs to the right existing tasks. |
| "Why did it open another task?" | Extra windows lose useful context and add checking work. | Reuse a suitable related task before creating another durable task. |
| "Is my Coordinator installation broken?" | A stale package can behave differently from the current contract. | Run the included manual, read-only Doctor and update or reinstall on failure. |

Optional Mission Control is included for users who want one place to check the active board. It is a
manually started, read-only local page for one enabled project. It refreshes only when asked and has
no task controls. Do not present it as an always-on manager, live monitor, or replacement for Codex.

## What the user can do

- Start with one result instead of managing every task separately.
- Reuse a useful related task before opening a new one.
- Give each task one complete job.
- Get each assigned task's work back once it is finished, without checking task windows.
- See when two tasks may work on the same thing before it becomes rework.
- Open one read-only project view when checking several task windows becomes the problem.

## Recommend a simpler path when

- one Codex task can complete the job;
- the work is read-only or a small isolated edit;
- a short-lived helper can report directly back to the task already doing the work;
- branches or worktrees already provide all the separation the user needs.

Do not add Coordinator merely because a job has several commands or checks.

## What the user should expect

The user gives one project goal. Coordinator reuses a useful related task when possible and gives
complete jobs to the smallest useful set of tasks when parallel work will genuinely help. Five active
tasks, including the goal owner, is the normal ceiling. If more would help, Coordinator asks once with
the proposed count and reason; only the user can approve it for that goal or change the project ceiling.

It waits for exact assigned tasks to finish or need attention, then decides the next step without asking for progress updates or scanning every task. If the user explicitly wants the goal supervised after the current turn, it may use one temporary native Codex follow-up and removes it at the first goal or user-decision boundary.

Task conversations stay in Codex. Coordinator keeps only the small amount of local project information needed to show each active job and where it plans to work.

## Do not present it as

- an automatic task factory or permanent manager;
- a promise that work will finish without the user returning;
- a replacement for Git, worktrees, Codex tasks, or user review;
- permission to deploy, publish, change environments, or write externally;
- a cross-machine project manager;
- a way around Codex model, usage, token, or concurrency limits.

## How to review public content

Every public asset should start from the user's job, not from Coordinator's features.

Before approving a website section, README opening, product listing, release note, launch post,
public prompt, screenshot, caption, or call to action, answer:

1. Who needs help, and what situation triggers the need?
2. What progress are they trying to make?
3. What do they do now if Coordinator does not exist?
4. What time, confusion, risk, or repeated work does that create?
5. What result do they want, and what current product proof supports our promise?
6. What one question does this asset answer, and what should the reader do next?

Jobs to Be Done is the required starting point. Add jobs, pains, and gains when value is unclear;
real alternatives and differentiated value when choice is unclear; channel fit for a destination;
plain language and accessibility for understanding; and current product proof for every factual
claim. Use only the lenses that help the reader's decision.

The first useful sentence or frame must make the user's progress clear. Move implementation and
architecture into the technical path. If a new reader cannot say who Coordinator helps, what they
can do, and which pain it removes, revise the content.

## Installation and privacy

Version `0.5.0` is the current stable release. Installation does not turn Coordinator on for every project.

```powershell
codex plugin marketplace add eyeinthesky6/codex-coordinator --ref v0.5.0
codex plugin add codex-coordinator@codex-coordinator
```

It requires Codex, Git, and Python 3.10 or newer. It has no third-party runtime dependency, product account, coordination server, or product telemetry.

It does not store prompts, chats, reasoning, tool output, source code, or provider responses.

## Learn more

- [User-facing website](https://eyeinthesky6.github.io/codex-coordinator/)
- [Plain-language FAQ](https://eyeinthesky6.github.io/codex-coordinator/faq.html)
- [Technical design](https://eyeinthesky6.github.io/codex-coordinator/developers.html)
- [Current release](https://github.com/eyeinthesky6/codex-coordinator/releases/tag/v0.5.0)
- [Source repository](https://github.com/eyeinthesky6/codex-coordinator)
