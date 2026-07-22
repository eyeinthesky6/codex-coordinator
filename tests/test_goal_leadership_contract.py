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
        self.assertIn("independently useful", execution)

    def test_lead_is_explicit_temporary_and_goal_scoped(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/execution.md")
        )
        self.assertIn("Never create a permanent lead task", content)
        self.assertIn("temporary lead", content)
        self.assertIn("role ends with the goal", content)
        self.assertNotIn("pinned Coordinator remains", content)

    def test_no_heartbeat_provider_or_schedule_reconciliation_contract(self) -> None:
        content = "\n".join(
            (SKILL_ROOT / path).read_text(encoding="utf-8")
            for path in ("SKILL.md", "references/operations.md", "references/execution.md")
        )
        self.assertIn("does not create a resident Coordinator", content)
        self.assertIn("does not create, pin, wake, or retain a Coordinator task", content)
        self.assertNotIn("verify exactly one repository heartbeat", content)
        self.assertNotIn("provider reconciliation", content.casefold())
        self.assertNotIn("per-turn reconciliation", content.casefold())

    def test_capability_contract_describes_boundary_board_not_orchestration(self) -> None:
        contract = json.loads((SKILL_ROOT / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contractVersion"], 20)
        capabilities = contract["capabilities"]
        self.assertEqual(capabilities["defaultExecution"], "one-native-task")
        self.assertEqual(capabilities["taskCreation"], "direct-user-or-independent-durable-lane")
        self.assertEqual(capabilities["transcriptStorage"], "none")
        self.assertEqual(capabilities["gitWorkflow"], "direct-commit-default-pr-optional")
        for removed in ("monitoring", "continuationGuarantee", "providerMonitoring", "scheduledTaskMonitoring"):
            self.assertNotIn(removed, capabilities)


if __name__ == "__main__":
    unittest.main()
