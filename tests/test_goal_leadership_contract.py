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
        self.assertIn("Three active durable tasks", skill)
        self.assertIn("Twelve is the hard board limit", skill)
        self.assertIn("substantial, complete vertical", execution)

    def test_explicit_coordinator_is_goal_scoped_and_on_demand(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md")
        )
        self.assertIn("explicitly requested Coordinator", content)
        self.assertIn("goal-scoped task", content)
        self.assertIn("two or three substantial verticals", content)
        self.assertIn("remains available when the user invokes it again", content)
        self.assertIn("exclusive `goal-coordination` action", content)
        self.assertIn("need not claim source paths", content)
        self.assertIn("does not wake the Coordinator automatically", content)
        self.assertIn("Do not promise automatic fan-in", content)
        self.assertIn("parent-owned subagents", content)
        self.assertNotIn("pinned Coordinator remains", content)

    def test_all_coordinated_tasks_share_checkout_branch_and_one_git_owner(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md")
        )
        self.assertIn("same primary checkout, current worktree, and current branch", content)
        self.assertIn("Do not create or switch branches or worktrees", content)
        self.assertIn("exactly one `git-integration`", content)
        self.assertIn("do not mutate Git state", content)

    def test_active_state_is_sparse_and_current_view_is_non_authoritative(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/operations.md", "references/execution.md")
        )
        self.assertIn("natural lifecycle boundaries", content)
        self.assertIn("non-authoritative, active-only view", content)
        self.assertIn("atomically rebuilt", content)
        self.assertIn("not an inbox", content)

    def test_no_heartbeat_provider_or_schedule_reconciliation_contract(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/operations.md", "references/execution.md")
        )
        self.assertIn("does not create background management", content)
        self.assertIn("does not automatically create, pin, wake, or retain a Coordinator task", content)
        self.assertIn("Do not poll task status", content)
        self.assertNotIn("verify exactly one repository heartbeat", content)
        self.assertNotIn("provider reconciliation", content.casefold())
        self.assertNotIn("per-turn reconciliation", content.casefold())

    def test_capability_contract_describes_boundary_board_not_orchestration(self) -> None:
        contract = json.loads((SKILL_ROOT / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contractVersion"], 26)
        capabilities = contract["capabilities"]
        self.assertEqual(capabilities["defaultExecution"], "one-native-task")
        self.assertEqual(
            capabilities["taskCreation"],
            "coordinator-two-or-three-complete-durable-verticals",
        )
        self.assertEqual(
            capabilities["goalCoordinator"],
            "user-invoked-goal-scoped-on-demand",
        )
        self.assertEqual(capabilities["goalCoordinationAction"], "goal-coordination")
        self.assertEqual(
            capabilities["taskPlacement"],
            "shared-primary-checkout-current-branch",
        )
        self.assertEqual(
            capabilities["dependentParallelism"],
            "durable-verticals-or-parent-owned-subagents",
        )
        self.assertEqual(
            capabilities["currentView"],
            "generated-active-only-non-authoritative",
        )
        self.assertEqual(capabilities["automaticFanIn"], "none")
        self.assertEqual(capabilities["transcriptStorage"], "none")
        self.assertEqual(
            capabilities["gitWorkflow"],
            "single-git-integration-owner-shared-checkout",
        )
        self.assertEqual(
            capabilities["stopGuard"], "own-active-claim-one-shot-no-transcript"
        )
        for removed in ("monitoring", "continuationGuarantee", "providerMonitoring", "scheduledTaskMonitoring"):
            self.assertNotIn(removed, capabilities)


if __name__ == "__main__":
    unittest.main()
