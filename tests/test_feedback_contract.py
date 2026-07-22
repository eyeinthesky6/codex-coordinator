from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SKILL = REPOSITORY / "plugins" / "codex-coordinator" / "skills" / "codex-coordinator"


class FeedbackContractTests(unittest.TestCase):
    def test_core_has_no_automatic_feedback_prompt_or_project_receipt(self) -> None:
        content = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                SKILL / "SKILL.md",
                SKILL / "references" / "execution.md",
                SKILL / "scripts" / "coordination_state.py",
            )
        ).casefold()
        self.assertNotIn("first field report", content)
        self.assertNotIn("feedback.json", content)
        self.assertNotIn("telegram", content)
        self.assertNotIn("after the first completed", content)


if __name__ == "__main__":
    unittest.main()
