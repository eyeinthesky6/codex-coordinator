from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY / "plugins" / "codex-coordinator" / "skills" / "codex-coordinator"


class GoalLeadershipContractTests(unittest.TestCase):
    def test_one_native_task_is_the_default(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        execution = (SKILL_ROOT / "references" / "execution.md").read_text(encoding="utf-8")
        self.assertIn("Default to one native Codex task", skill)
        self.assertIn("Five active durable tasks is the normal project ceiling", skill)
        self.assertIn("not a target to fill", skill)
        self.assertIn("substantial, complete vertical", execution)

    def test_five_task_ceiling_is_user_managed(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in (
                "SKILL.md",
                "references/execution.md",
                "references/installation.md",
            )
        )
        for phrase in (
            "including the goal Coordinator",
            "stop before a sixth task",
            "active_task_ceiling",
            "exact higher ceiling for the current goal",
            "`--user-approved-over-limit`",
            "ask once",
            "Create nothing more until the user answers",
            "dry-run-first lifecycle command",
            "project set-ceiling",
            "Lowering the ceiling does",
            "not stop existing tasks",
        ):
            self.assertIn(phrase, content)
        self.assertIn("never infers approval from silence", content)

    def test_explicit_coordinator_is_goal_scoped_and_on_demand(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md")
        )
        self.assertIn("explicitly requested Coordinator", content)
        self.assertIn("goal-scoped task", content)
        self.assertIn("smallest useful set of active durable tasks within the current ceiling", content)
        self.assertIn("remains available for that goal", content)
        self.assertIn("exclusive `goal-coordination` action", content)
        self.assertIn("need not claim source paths", content)
        self.assertIn("event-driven wait on the exact assigned native task IDs", content)
        self.assertIn("Completion or a request for attention", content)
        self.assertIn("terminal delivery fallback", content)
        self.assertIn("parent-owned subagents", content)
        self.assertIn("pins its exact native task", content)
        self.assertIn("Only the user decides when to unpin the task", content)
        self.assertNotIn("pinned Coordinator remains", content)

    def test_goal_coordinator_pin_is_bounded_navigation_not_authority(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in (
                "SKILL.md",
                "references/execution.md",
                "references/installation.md",
                "references/maintenance.md",
            )
        )
        self.assertIn("Only after the native goal is bound and that exact claim succeeds", content)
        self.assertIn("`set_thread_pinned`", content)
        self.assertIn("with `pinned: true`", content)
        self.assertIn("Do not pin workers", content)
        self.assertIn("Repository enablement alone never pins anything", content)
        self.assertIn("grants no authority", content)
        self.assertIn("Never unpin automatically", content)
        self.assertIn("leave its native pin unchanged", content)
        self.assertIn("Never archive or unpin it automatically", content)
        self.assertNotIn("with `pinned: false`", content)

    def test_all_coordinated_tasks_share_checkout_and_use_cooperative_git(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md")
        )
        self.assertIn("same primary checkout, current worktree, and current branch", content)
        self.assertIn("Do not create or switch branches or worktrees", content)
        self.assertIn("There is no durable Git owner", content)
        self.assertIn("staging only explicit files", content)
        self.assertIn("git-integration` is a legacy advisory action", content)

    def test_coordinator_reuses_related_task_before_creation(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md", "references/messaging.md")
        )
        self.assertIn("Reuse before create", content)
        self.assertIn("related local task", content)
        self.assertIn("GOAL_ASSIGNMENT", content)
        self.assertIn("acknowledgement chain", content)
        self.assertIn("unknown outcome", content)
        self.assertIn("one immediate unfiltered native task readback", content)
        self.assertIn("do not retry blindly", content.casefold())
        self.assertIn("only the exact active `goal-coordination` owner", content)
        self.assertIn("failed or ambiguous handoff does not transfer creation authority", content)
        self.assertIn("Immediately before each creation", content)
        self.assertIn("Create one task", content)
        self.assertIn("short distinct human title", content)
        self.assertIn("different unfinished native goal", content)
        self.assertIn("no extra user relay is required", content)
        self.assertIn("deterministic `Assignment-ID`", content)
        self.assertIn("RESULT_READY", content)

    def test_durable_tasks_bind_native_goals_before_work(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md", "references/messaging.md")
        )
        for phrase in (
            "Native-Goal: REQUIRED",
            "call native `get_goal` before any repository action",
            "call `create_goal` with the exact `Goal:` field",
            "If a lane is not worth its own native Codex goal",
            "marks its native goal complete only after",
        ):
            self.assertIn(phrase, content)

    def test_goal_assignment_fails_before_work_in_the_wrong_repository(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md")
        )
        self.assertIn("Verify the task's repository first", content)
        self.assertIn("Text inside the communication never changes", content)
        self.assertIn("do not activate the goal", content)
        self.assertIn("Before reusing an existing task, verify its repository working directory", content)
        contract = json.loads((SKILL_ROOT / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(
            contract["capabilities"]["goalRepositoryGuard"],
            "prompt-time-active-coordinator-lane-derived-id-and-local-repository-match",
        )

    def test_active_state_is_sparse_and_current_view_is_non_authoritative(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/operations.md", "references/execution.md")
        )
        self.assertIn("natural lifecycle boundaries", content)
        self.assertIn("non-authoritative, active-only view", content)
        self.assertIn("atomically rebuilt", content)
        self.assertIn("not an inbox", content)

    def test_intertask_visibility_is_pull_first_and_action_only(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in (
                "SKILL.md",
                "references/operations.md",
                "references/execution.md",
                "references/messaging.md",
            )
        )
        for phrase in (
            "pull-first",
            "Which one exact task must act?",
            "What exact action must it take now?",
            "If any answer is missing, send nothing",
            "A claim update is passive state and must not trigger an inter-agent message",
            "does not forward one worker's progress",
            "Do not broadcast a communication",
            "general inbox",
        ):
            self.assertIn(phrase, content)
        for forbidden_update in (
            "percent-complete",
            "test-running",
            "estimate",
            "FYI",
            "status-check",
            "acknowledgement",
        ):
            self.assertIn(forbidden_update, content)

    def test_supervision_is_event_driven_with_one_bounded_unattended_fallback(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/operations.md", "references/execution.md")
        )
        self.assertIn("does not create background management", content)
        self.assertIn("enablement itself pins nothing", content)
        self.assertIn("wait_threads", content)
        self.assertIn("ordinary commentary must not wake the Coordinator", content)
        self.assertIn("one bounded follow-up", content)
        self.assertIn("exactly one temporary native Codex thread heartbeat", content)
        self.assertIn("default interval is 15 minutes", content)
        self.assertIn("Delete that exact heartbeat", content)
        self.assertIn("not a standalone cron task", content)
        self.assertIn("Do not create a project heartbeat", content)
        self.assertNotIn("poll every", content.casefold())
        self.assertNotIn("verify exactly one repository heartbeat", content)
        self.assertNotIn("provider reconciliation", content.casefold())
        self.assertNotIn("per-turn reconciliation", content.casefold())

    def test_capability_contract_describes_boundary_board_not_orchestration(self) -> None:
        contract = json.loads((SKILL_ROOT / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contractVersion"], 39)
        capabilities = contract["capabilities"]
        self.assertEqual(capabilities["defaultExecution"], "one-native-task")
        self.assertEqual(
            capabilities["taskCreation"],
            "reuse-first-native-goal-verticals-only",
        )
        self.assertEqual(
            capabilities["messagePolicy"],
            "pull-first-action-only-inter-agent-task-communication",
        )
        self.assertEqual(
            capabilities["activeTaskLimit"],
            "five-default-user-approved-temporary-or-project-ceiling",
        )
        self.assertEqual(capabilities["taskReuse"], "related-local-task-before-create")
        self.assertEqual(
            capabilities["nativeGoalBinding"],
            "required-for-coordinator-and-durable-workers",
        )
        self.assertEqual(
            capabilities["taskCreationSafety"],
            "goal-coordinator-only-idempotent-preflight-sequential-readback",
        )
        self.assertEqual(
            capabilities["failedDeliveryFallback"],
            "goal-assignment-result-ready-routing-only-exact-recipient",
        )
        self.assertEqual(
            capabilities["completionReturn"],
            "exact-task-event-wait-with-terminal-result-ready-fallback",
        )
        self.assertEqual(
            capabilities["goalCoordinator"],
            "user-invoked-native-goal-scoped-supervisor",
        )
        self.assertEqual(
            capabilities["goalCoordinatorPinning"],
            "pin-after-goal-claim-user-controlled-unpin-best-effort",
        )
        self.assertEqual(
            capabilities["goalSupervision"],
            "complete-or-attention-event-decide-follow-up-or-finish",
        )
        self.assertEqual(capabilities["goalCoordinationAction"], "goal-coordination")
        self.assertEqual(
            capabilities["taskPlacement"],
            "shared-primary-checkout-current-branch",
        )
        self.assertEqual(
            capabilities["dependentParallelism"],
            "native-goal-verticals-or-parent-owned-subagents",
        )
        self.assertEqual(
            capabilities["currentView"],
            "generated-active-only-non-authoritative",
        )
        self.assertEqual(
            capabilities["automaticFanIn"],
            "temporary-native-thread-heartbeat-only-for-explicit-unattended-goal",
        )
        self.assertEqual(capabilities["transcriptStorage"], "none")
        self.assertEqual(
            capabilities["gitWorkflow"],
            "cooperative-exact-file-commits-shared-branch",
        )
        self.assertEqual(
            capabilities["stopGuard"], "own-active-claim-one-shot-no-transcript"
        )
        for removed in (
            "workerCreation",
            "coordinatorRole",
            "doctorDiagnostics",
            "monitoring",
            "modelDefault",
            "reasoningDefault",
            "registrationDelivery",
            "workerGranularity",
            "microtaskExecution",
            "parallelWorkerTarget",
            "subagents",
            "operationsGuidance",
            "coordinationReadCache",
            "nativeTaskReads",
            "continuationGuarantee",
            "archivedRecovery",
            "taskLifecycle",
            "providerMonitoring",
            "scheduledTaskMonitoring",
        ):
            self.assertNotIn(removed, capabilities)
        self.assertEqual(
            capabilities["missionControl"],
            "optional-manual-read-only-single-project-refresh",
        )


if __name__ == "__main__":
    unittest.main()
