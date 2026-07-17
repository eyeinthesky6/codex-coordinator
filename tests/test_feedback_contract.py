import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXECUTION = (
    ROOT
    / "plugins"
    / "codex-coordinator"
    / "skills"
    / "codex-coordinator"
    / "references"
    / "execution.md"
)


class FeedbackContractTests(unittest.TestCase):
    def test_first_field_report_is_optional_local_and_once_per_project(self):
        text = EXECUTION.read_text(encoding="utf-8")

        self.assertIn("### Optional first field report", text)
        self.assertIn(".codex/coordination/feedback.json", text)
        self.assertIn('"status": "requested"', text)
        self.assertIn("discussions/new?category=ideas", text)
        self.assertIn("do not overwrite it and do not repeat the request", text)
        self.assertIn("The prompt is never an acceptance gate", text)
        self.assertIn("nothing is sent automatically", text)
        self.assertIn("`opened` or `dismissed`", text)
        self.assertIn("never claims the user submitted it", text)

        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".codex/coordination/*", ignore)
        self.assertIn("!.codex/coordination/project.yaml", ignore)


if __name__ == "__main__":
    unittest.main()
