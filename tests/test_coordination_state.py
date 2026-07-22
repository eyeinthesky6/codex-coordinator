from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
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


THREADS = [f"{index:08x}-1111-4111-8111-{index:012x}" for index in range(1, 20)]


def _project(directory: str, *, enabled: bool = True) -> Path:
    root = Path(directory)
    marker = root / ".codex" / "coordination" / "project.yaml"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        "\n".join(
            [
                "schema_version: 2",
                f"coordination_enabled: {'true' if enabled else 'false'}",
                "project_id: sample",
                "canonical_paths:",
                "  active: .codex/coordination/active",
                "  archive: .codex/coordination/archive",
                "access:",
                "  cross_project_task_access: false",
                "  cross_project_state_changes: false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root


def _claim(root: Path, index: int, path: str, **overrides):
    values = {
        "thread_id": THREADS[index],
        "title": f"Task {index}",
        "goal": f"Own bounded area {index}",
        "paths": [path],
        "actions": [],
        "blocked_by": [],
        "status": "active",
        "expected_revision": 0,
        "user_approved_over_limit": False,
    }
    values.update(overrides)
    return state.claim_boundary(root, **values)


class CoordinationStateTests(unittest.TestCase):
    def test_empty_board_is_small_and_has_fixed_limits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = state.list_board(_project(directory))
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["activeCount"], 0)
        self.assertEqual(report["defaultLimit"], 3)
        self.assertEqual(report["hardLimit"], 12)
        self.assertEqual(report["records"], [])

    def test_disabled_project_reads_no_board(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory, enabled=False)
            active = root / ".codex" / "coordination" / "active"
            active.mkdir()
            (active / "broken.json").write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(state.BoardError, "disabled"):
                state.list_board(root)

    def test_claim_updates_only_exact_owner_with_revision_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            created = _claim(root, 0, "src/a")
            self.assertEqual(created["status"], "claimed")
            self.assertEqual(created["record"]["revision"], 1)
            target = root / ".codex" / "coordination" / "active" / f"{THREADS[0]}.json"
            original = target.read_bytes()

            with self.assertRaisesRegex(state.BoardError, "revision changed"):
                _claim(root, 0, "src/b", expected_revision=0)
            self.assertEqual(target.read_bytes(), original)

            updated = _claim(root, 0, "src/b", expected_revision=1)
            self.assertEqual(updated["status"], "updated")
            self.assertEqual(updated["record"]["revision"], 2)
            self.assertEqual(updated["record"]["paths"], ["src/b"])

    def test_disjoint_claims_proceed_without_messages_or_central_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            _claim(root, 0, "src/a")
            _claim(root, 1, "docs/b")
            report = state.list_board(root)
        self.assertEqual(report["activeCount"], 2)
        self.assertEqual(report["conflicts"], [])
        self.assertFalse(any("coordinator" in key.casefold() for key in report))

    def test_ancestor_case_and_repository_wide_paths_conflict(self) -> None:
        cases = (("src", "src/app.py"), ("SRC/App.py", "src/app.py"), (".", "docs/a.md"))
        for owned, requested in cases:
            with self.subTest(owned=owned, requested=requested), tempfile.TemporaryDirectory() as directory:
                root = _project(directory)
                _claim(root, 0, owned)
                with self.assertRaises(state.ClaimConflict) as raised:
                    _claim(root, 1, requested)
                conflict = raised.exception.conflicts[0]
                self.assertEqual(conflict["threadId"], THREADS[0])
                self.assertTrue(conflict["pathOverlaps"])

    def test_exact_exclusive_action_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            _claim(root, 0, "src/a", actions=["git-integration"])
            with self.assertRaises(state.ClaimConflict):
                _claim(root, 1, "docs/b", actions=["git-integration"])

    def test_default_and_hard_task_limits_require_user_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            for index in range(3):
                _claim(root, index, f"area/{index}")
            with self.assertRaisesRegex(state.BoardError, "direct user decision"):
                _claim(root, 3, "area/3")
            _claim(root, 3, "area/3", user_approved_over_limit=True)
            for index in range(4, 12):
                _claim(root, index, f"area/{index}", user_approved_over_limit=True)
            with self.assertRaisesRegex(state.BoardError, "hard limit"):
                _claim(root, 12, "area/12", user_approved_over_limit=True)
            self.assertEqual(state.list_board(root)["activeCount"], 12)

    def test_claim_schema_rejects_transcripts_unknown_fields_and_large_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            record = _claim(root, 0, "src/a")["record"]
            target = root / ".codex" / "coordination" / "active" / f"{THREADS[0]}.json"
            record["transcript"] = "private task text"
            target.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(state.BoardError, "unsupported fields"):
                state.list_board(root)

            target.write_text("{\"schemaVersion\":1," + "\"x\":\"" + ("a" * 5000) + "\"}", encoding="utf-8")
            with self.assertRaisesRegex(state.BoardError, "exceeds"):
                state.list_board(root)

    def test_claim_schema_does_not_coerce_non_text_path_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            with self.assertRaisesRegex(state.BoardError, "must be text"):
                _claim(root, 0, "src/a", paths=[123])

    def test_board_rejects_symlinked_active_directory_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            external = Path(directory) / "external"
            external.mkdir()
            active = root / ".codex" / "coordination" / "active"
            try:
                active.symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlinks are unavailable")
            with self.assertRaisesRegex(state.BoardError, "symlink or junction"):
                state.list_board(root)

    def test_invalid_identity_and_paths_fail_before_write(self) -> None:
        bad_paths = ("../secret", "/absolute", "C:/secret", "src/*.py", "src/./file")
        for bad_path in bad_paths:
            with self.subTest(path=bad_path), tempfile.TemporaryDirectory() as directory:
                root = _project(directory)
                with self.assertRaises(state.BoardError):
                    _claim(root, 0, bad_path)
                self.assertEqual(state.list_board(root)["activeCount"], 0)
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            with self.assertRaisesRegex(state.BoardError, "exact native"):
                _claim(root, 0, "src/a", thread_id="worker")

    def test_release_removes_hot_claim_and_writes_compact_cold_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            _claim(root, 0, "src/a", actions=["git-integration"])
            released = state.release_boundary(
                root,
                thread_id=THREADS[0],
                expected_revision=1,
                final_status="completed",
            )
            self.assertEqual(released["status"], "released")
            self.assertEqual(state.list_board(root)["activeCount"], 0)
            receipts = list((root / ".codex" / "coordination" / "archive").glob("*.json"))
            self.assertEqual(len(receipts), 1)
            receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
            self.assertNotIn("paths", receipt)
            self.assertNotIn("actions", receipt)
            self.assertNotIn("transcript", receipt)
            self.assertLess(receipts[0].stat().st_size, 1024)

    def test_conflicting_concurrent_claims_leave_one_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            barrier = threading.Barrier(2)
            outcomes: list[str] = []

            def worker(index: int) -> None:
                barrier.wait()
                try:
                    _claim(root, index, "shared/path")
                    outcomes.append("claimed")
                except state.ClaimConflict:
                    outcomes.append("conflict")

            threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertEqual(sorted(outcomes), ["claimed", "conflict"])
            self.assertEqual(state.list_board(root)["activeCount"], 1)

    def test_source_contains_no_ledger_inbox_or_transcript_reader(self) -> None:
        source = STATE_TOOL.read_text(encoding="utf-8")
        for forbidden in ("CURRENT.md", "scan_inbox", "rollout", "sqlite", "transcript"):
            if forbidden == "transcript":
                self.assertIn("never reads or\nstores task transcripts", source)
            else:
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
