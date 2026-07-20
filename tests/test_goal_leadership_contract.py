from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY / "plugins" / "codex-coordinator" / "skills" / "codex-coordinator"


class GoalLeadershipContractTests(unittest.TestCase):
    def test_worker_completion_cannot_replace_goal_completion(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        reconciliation = (SKILL_ROOT / "references" / "reconciliation.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("owns delivery of the user's shared goal", skill)
        self.assertIn("goal-coverage ledger", skill)
        self.assertIn("A worker reaching a terminal state", skill)
        self.assertIn("Goal coverage and team-leader loop", reconciliation)
        self.assertIn("Closing every worker does not close the shared goal", reconciliation)
        self.assertIn("absence of a worker is not a disposition", reconciliation)

    def test_no_change_is_never_a_terminal_signal(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        reconciliation = (SKILL_ROOT / "references" / "reconciliation.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Treat `no change` only as an observation", skill)
        self.assertIn("It never means done, idle, terminal", skill)
        self.assertIn("A no-change heartbeat preserves", reconciliation)
        self.assertIn("It is not a completion event", reconciliation)

    def test_leader_selects_the_next_delivery_path(self) -> None:
        reconciliation = (SKILL_ROOT / "references" / "reconciliation.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("highest-value executable action on the critical path", reconciliation)
        self.assertIn("another currently available in-scope tool", reconciliation)
        self.assertIn("one concise, prioritised decision request", reconciliation)
        self.assertIn("Suggest a correction or safer next path", reconciliation)
        self.assertIn("Never reduce the report to worker activity", reconciliation)

    def test_enabled_repository_lifecycle_is_active_by_default(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        installation = (SKILL_ROOT / "references" / "installation.md").read_text(encoding="utf-8")
        reconciliation = (SKILL_ROOT / "references" / "reconciliation.md").read_text(encoding="utf-8")

        self.assertIn("Every same-repository Codex task is managed by default", skill)
        self.assertIn("Only a direct user instruction may add or remove", skill)
        self.assertIn("A user pause switches to `REPORT_ONLY`", skill)
        self.assertIn("workload idle never unregisters the Coordinator", skill)
        self.assertIn("create one complete native Coordinator task", installation)
        self.assertIn("lists excluded tasks or `none`", reconciliation)


if __name__ == "__main__":
    unittest.main()
