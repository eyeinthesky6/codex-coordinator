from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
STATE_TOOL = (
    REPOSITORY
    / "plugins"
    / "codex-coordinator"
    / "skills"
    / "codex-coordinator"
    / "scripts"
    / "coordination_state.py"
)
SPEC = importlib.util.spec_from_file_location("coordination_state", STATE_TOOL)
assert SPEC and SPEC.loader
state = importlib.util.module_from_spec(SPEC)
sys.dont_write_bytecode = True
SPEC.loader.exec_module(state)


def _current(*, shared_goal: str = "none", task_id: str = "NONE") -> str:
    return f"""# Codex Coordinator state

**Project ID:** sample
**Coordination epoch:** 0
**Coordination mode:** IDLE
**Shared goal:** {shared_goal}
**Last reconciliation:** 2026-07-16T12:00:00+00:00
**Coordinator thread ID:** 11111111-1111-4111-8111-111111111111
**Coordinator thread name:** Sample Coordinator
**Coordinator status:** IDLE
**Accepts project messages:** true

## Registered sessions

| Thread ID | Thread name | Scope kind | Role | Task ID | Status | Accepts project messages |
| --- | --- | --- | --- | --- | --- | --- |
| 11111111-1111-4111-8111-111111111111 | Sample Coordinator | PROJECT_EXECUTION | COORDINATOR | {task_id} | IDLE | true |

## Active tasks

| Task ID | Owner | Role | Status |
| --- | --- | --- | --- |

## Pending commands

| Task ID | Message ID | Recipient thread ID | Message type | Status |
| --- | --- | --- | --- | --- |

## Paused work

| Task ID | Owner | Reason | Resume condition | Status |
| --- | --- | --- | --- | --- | --- |

## Resume queue

| Task ID | Message ID | Resume condition | Status |
| --- | --- | --- | --- |

## Blocked decisions

| Decision ID | Task ID | Decision needed | Status |
| --- | --- | --- | --- |
"""


class CoordinationStateTests(unittest.TestCase):
    def test_validate_and_normalize_harmless_taskless_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CURRENT.md"
            path.write_text(
                _current(shared_goal="No active coordinated goal.", task_id="-"),
                encoding="utf-8",
            )

            report = state.validate_current(path)
            self.assertEqual(report["status"], "valid")
            self.assertEqual(report["fields"]["Shared goal"], "none")
            self.assertEqual(len(report["normalizations"]), 2)
            self.assertIn("No active coordinated goal.", path.read_text(encoding="utf-8"))

            normalized = state.normalize_current(path)
            self.assertEqual(normalized["status"], "normalized")
            text = path.read_text(encoding="utf-8")
            self.assertIn("**Shared goal:** none", text)
            self.assertIn("| COORDINATOR | NONE | IDLE |", text)
            self.assertEqual(normalized["normalizations"], [])

    def test_validate_current_rejects_missing_required_table_column(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CURRENT.md"
            path.write_text(
                _current().replace(" | Accepts project messages |", " |"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(state.StateError, "missing, duplicate, or unknown"):
                state.validate_current(path)

    def test_validate_current_rejects_invalid_required_metadata(self) -> None:
        replacements = {
            "blank project": ("**Project ID:** sample", "**Project ID:** ", "Project ID"),
            "invalid epoch": (
                "**Coordination epoch:** 0",
                "**Coordination epoch:** not-a-number",
                "Coordination epoch",
            ),
            "invalid acceptance": (
                "**Accepts project messages:** true",
                "**Accepts project messages:** sometimes",
                "Accepts project messages",
            ),
        }
        for name, (before, after, error) in replacements.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "CURRENT.md"
                path.write_text(_current().replace(before, after), encoding="utf-8")
                with self.assertRaisesRegex(state.StateError, error):
                    state.validate_current(path)

    def test_reconciliation_requires_known_status_and_nonempty_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            path.write_text(
                """type: TURN_RECONCILIATION
project_id: sample
coordination_epoch: 1
message_id: REPORT-1
reported_by_thread: worker
related_task_id: SAMPLE-1
state: REPORTING

| Task or promise | Relationship to shared goal | Status | Evidence or remaining work | Recommended disposition |
| --- | --- | --- | --- | --- |
| Repair parser | Direct | DONE | Tests passed | Close |
""",
                encoding="utf-8",
            )
            report = state.validate_reconciliation(path)
            self.assertEqual(report["ledgerRows"][0]["Status"], "DONE")

            path.write_text(path.read_text(encoding="utf-8").replace("DONE", "MAYBE"), encoding="utf-8")
            with self.assertRaisesRegex(state.StateError, "Unknown reconciliation status"):
                state.validate_reconciliation(path)

    def test_reconciliation_requires_valid_epoch_and_reporting_state(self) -> None:
        template = """type: TURN_RECONCILIATION
project_id: sample
coordination_epoch: {epoch}
message_id: REPORT-1
reported_by_thread: worker
related_task_id: SAMPLE-1
state: {record_state}

| Task or promise | Relationship to shared goal | Status | Evidence or remaining work | Recommended disposition |
| --- | --- | --- | --- | --- |
| Repair parser | Direct | DONE | Tests passed | Close |
"""
        cases = {
            "invalid epoch": ("not-a-number", "REPORTING", "coordination_epoch"),
            "invalid state": ("1", "CLAIMING_AUTHORITY", "state"),
        }
        for name, (epoch, record_state, error) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                path.write_text(
                    template.format(epoch=epoch, record_state=record_state),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(state.StateError, error):
                    state.validate_reconciliation(path)

    def test_create_file_is_scoped_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".codex" / "coordination"
            report = state.create_file(root, Path("inbox/report.md"), b"report\n")
            self.assertEqual(report["status"], "created")
            self.assertEqual((root / "inbox" / "report.md").read_text(), "report\n")

            with self.assertRaisesRegex(state.StateError, "Refusing to overwrite"):
                state.create_file(root, Path("inbox/report.md"), b"new\n")
            with self.assertRaisesRegex(state.StateError, "tasks/ or inbox"):
                state.create_file(root, Path("CURRENT.md"), b"unsafe\n")
            with self.assertRaisesRegex(state.StateError, "tasks/ or inbox"):
                state.create_file(root, Path("tasks/../CURRENT.md"), b"unsafe\n")


if __name__ == "__main__":
    unittest.main()
