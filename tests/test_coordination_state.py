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

    def test_inspect_current_returns_only_validated_structured_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CURRENT.md"
            path.write_text(_current(), encoding="utf-8")

            report = state.inspect_current(path)

            self.assertEqual(report["status"], "valid")
            self.assertEqual(report["fields"]["Project ID"], "sample")
            self.assertEqual(len(report["tables"]["Registered sessions"]), 1)
            self.assertEqual(
                report["tables"]["Registered sessions"][0]["Role"], "COORDINATOR"
            )
            self.assertEqual(report["tables"]["Active tasks"], [])

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

    def test_validate_current_rejects_malformed_and_duplicate_rows(self) -> None:
        active_header = "| Task ID | Owner | Role | Status |\n| --- | --- | --- | --- |"
        cases = {
            "blank row": active_header + "\n| | | | |",
            "duplicate task": active_header
            + "\n| SAMPLE-1 | 11111111-1111-4111-8111-111111111111 | COORDINATOR | ACTIVE |"
            + "\n| SAMPLE-1 | Worker | TASK_AGENT | ACTIVE |",
            "invalid task": active_header
            + "\n| task with spaces | 11111111-1111-4111-8111-111111111111 | COORDINATOR | ACTIVE |",
        }
        for name, replacement in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "CURRENT.md"
                path.write_text(_current().replace(active_header, replacement), encoding="utf-8")
                with self.assertRaises(state.StateError):
                    state.validate_current(path)

    def test_validate_current_matches_hook_text_safety(self) -> None:
        replacements = {
            "control in goal": ("**Shared goal:** none", "**Shared goal:** unsafe\tgoal"),
            "control in name": (
                "**Coordinator thread name:** Sample Coordinator",
                "**Coordinator thread name:** Unsafe\tCoordinator",
            ),
        }
        for name, (before, after) in replacements.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "CURRENT.md"
                path.write_text(_current().replace(before, after), encoding="utf-8")
                with self.assertRaises(state.StateError):
                    state.validate_current(path)

    def test_normalization_preserves_windows_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CURRENT.md"
            original = _current(
                shared_goal="No active coordinated goal.", task_id="-"
            ).replace("\n", "\r\n")
            path.write_bytes(original.encode("utf-8"))

            state.normalize_current(path)

            updated = path.read_bytes()
            self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))
            self.assertIn(b"**Shared goal:** none\r\n", updated)
            self.assertIn(b"| COORDINATOR | NONE | IDLE |", updated)

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

    def test_reconciliation_rejects_invalid_ids_and_ledger_rows(self) -> None:
        template = """type: TURN_RECONCILIATION
project_id: sample
coordination_epoch: 1
message_id: {message_id}
reported_by_thread: worker
related_task_id: {task_id}
state: REPORTING

| Task or promise | Relationship to shared goal | Status | Evidence or remaining work | Recommended disposition |
| --- | --- | --- | --- | --- |
{rows}
"""
        cases = {
            "invalid message id": ("bad id", "SAMPLE-1", "| Repair | Direct | DONE | Tests | Close |"),
            "invalid task id": ("REPORT-1", "bad task", "| Repair | Direct | DONE | Tests | Close |"),
            "blank cells": ("REPORT-1", "SAMPLE-1", "| | Direct | DONE | | Close |"),
            "duplicate row": (
                "REPORT-1",
                "SAMPLE-1",
                "| Repair | Direct | DONE | Tests | Close |\n| Repair | Direct | DONE | Tests | Close |",
            ),
        }
        for name, (message_id, task_id, rows) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "report.md"
                path.write_text(
                    template.format(message_id=message_id, task_id=task_id, rows=rows),
                    encoding="utf-8",
                )
                with self.assertRaises(state.StateError):
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

    def test_inbox_checkpoint_requires_explicit_acknowledgement(self) -> None:
        coordinator_id = "11111111-1111-4111-8111-111111111111"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".codex" / "coordination"
            state.create_file(root, Path("inbox/one.md"), b"first\n")

            first = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )
            self.assertEqual(first["status"], "pending")
            self.assertEqual(first["cacheStatus"], "missing")
            self.assertEqual(first["pendingRecords"][0]["reason"], "new")
            self.assertFalse((root / "cache" / "inbox-index.json").exists())

            repeated = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )
            self.assertEqual(len(repeated["pendingRecords"]), 1)

            record = first["pendingRecords"][0]
            acknowledged = state.acknowledge_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
                records={"one.md": record["sha256"]},
            )
            self.assertEqual(acknowledged["status"], "acknowledged")
            self.assertTrue((root / "cache" / "inbox-index.json").is_file())

            current = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )
            self.assertEqual(current["status"], "current")
            self.assertEqual(current["pendingRecords"], [])
            self.assertEqual(current["acknowledgedCount"], 1)

            (root / "inbox" / "one.md").unlink()
            missing = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )
            self.assertEqual(missing["status"], "pending")
            self.assertEqual(missing["staleAcknowledgements"], ["inbox/one.md"])
            self.assertIn("acknowledged_record_missing:one.md", missing["warnings"])

    def test_inbox_checkpoint_detects_changes_and_never_acks_stale_hashes(self) -> None:
        coordinator_id = "11111111-1111-4111-8111-111111111111"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".codex" / "coordination"
            path = root / "inbox" / "one.md"
            state.create_file(root, Path("inbox/one.md"), b"first\n")
            initial = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )["pendingRecords"][0]
            state.acknowledge_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
                records={"one.md": initial["sha256"]},
            )

            path.write_bytes(b"changed\n")
            changed = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )
            self.assertEqual(changed["pendingRecords"][0]["reason"], "changed")
            self.assertIn("acknowledged_record_changed:one.md", changed["warnings"])
            with self.assertRaisesRegex(state.StateError, "changed before acknowledgement"):
                state.acknowledge_inbox(
                    root,
                    project_id="sample",
                    coordination_epoch=1,
                    coordinator_id=coordinator_id,
                    records={"one.md": initial["sha256"]},
                )

    def test_inbox_checkpoint_rebuilds_on_scope_change_or_corrupt_cache(self) -> None:
        coordinator_id = "11111111-1111-4111-8111-111111111111"
        replacement_id = "22222222-2222-4222-8222-222222222222"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".codex" / "coordination"
            state.create_file(root, Path("inbox/one.md"), b"first\n")
            record = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )["pendingRecords"][0]
            state.acknowledge_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
                records={"one.md": record["sha256"]},
            )

            replaced = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=replacement_id,
            )
            self.assertEqual(replaced["cacheStatus"], "scope_changed")
            self.assertEqual(len(replaced["pendingRecords"]), 1)

            (root / "cache" / "inbox-index.json").write_text("{broken", encoding="utf-8")
            corrupt = state.scan_inbox(
                root,
                project_id="sample",
                coordination_epoch=1,
                coordinator_id=coordinator_id,
            )
            self.assertEqual(corrupt["cacheStatus"], "corrupt")
            self.assertEqual(len(corrupt["pendingRecords"]), 1)

    def test_inbox_ack_parser_rejects_paths_and_duplicate_records(self) -> None:
        digest = "a" * 64
        self.assertEqual(
            state._parse_acknowledgements([f"inbox/one.md={digest}"]),
            {"one.md": digest},
        )
        for value in (
            f"tasks/one.md={digest}",
            f"inbox/../one.md={digest}",
            "inbox/one.md=bad",
        ):
            with self.subTest(value=value), self.assertRaises(state.StateError):
                state._parse_acknowledgements([value])
        with self.assertRaisesRegex(state.StateError, "Duplicate"):
            state._parse_acknowledgements(
                [f"inbox/one.md={digest}", f"inbox/one.md={digest}"]
            )


if __name__ == "__main__":
    unittest.main()
