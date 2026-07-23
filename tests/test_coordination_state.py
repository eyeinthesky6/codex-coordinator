from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_current_view_tracks_create_update_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            current = root / ".codex" / "coordination" / "CURRENT.md"

            _claim(
                root,
                0,
                "src/a",
                actions=["goal-coordination", "git-integration"],
            )
            created = current.read_text(encoding="utf-8")
            self.assertIn("Generated active-only view", created)
            self.assertIn(THREADS[0], created)
            self.assertIn("Coordinator:", created)
            self.assertIn("Shared goal: Own bounded area 0", created)
            self.assertIn("path: src/a", created)
            self.assertIn("Git integration owner:", created)

            current.write_text("corrupt stale view\n", encoding="utf-8")
            _claim(
                root,
                0,
                "src/b",
                expected_revision=1,
                title="Updated lane",
                goal="Updated bounded goal",
                status="blocked",
                actions=["goal-coordination", "git-integration"],
            )
            updated = current.read_text(encoding="utf-8")
            self.assertNotIn("corrupt stale view", updated)
            self.assertNotIn("Own bounded area 0", updated)
            self.assertNotIn("path: src/a", updated)
            self.assertIn("Updated lane", updated)
            self.assertIn("Updated bounded goal", updated)
            self.assertIn("path: src/b", updated)
            self.assertIn("blocked", updated)

            current.unlink()
            state.release_boundary(
                root,
                thread_id=THREADS[0],
                expected_revision=2,
                final_status="completed",
            )
            released = current.read_text(encoding="utf-8")
            self.assertIn("Active lanes: 0", released)
            self.assertNotIn(THREADS[0], released)
            self.assertNotIn("Updated lane", released)
            self.assertNotIn("Updated bounded goal", released)

    def test_current_view_never_reads_private_or_historical_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            coordination = root / ".codex" / "coordination"
            archive = coordination / "archive"
            archive.mkdir()
            (coordination / "private.jsonl").write_text(
                "PRIVATE_TRANSCRIPT_SENTINEL", encoding="utf-8"
            )
            (archive / "old.json").write_text(
                json.dumps({"goal": "ARCHIVED_HISTORY_SENTINEL"}), encoding="utf-8"
            )

            _claim(root, 0, "src/a")
            current = (coordination / "CURRENT.md").read_text(encoding="utf-8")
            self.assertNotIn("PRIVATE_TRANSCRIPT_SENTINEL", current)
            self.assertNotIn("ARCHIVED_HISTORY_SENTINEL", current)
            self.assertNotIn("Coordinator:", current)
            self.assertNotIn("Shared goal:", current)
            for private_field in ("createdAt", "updatedAt", "revision", "closedAt"):
                self.assertNotIn(private_field, current)

    def test_repeated_release_in_one_second_uses_unique_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            state, "_now", return_value="2026-07-23T04:42:08Z"
        ):
            root = _project(directory)
            for cycle in range(2):
                _claim(root, 0, f"src/cycle-{cycle}")
                released = state.release_boundary(
                    root,
                    thread_id=THREADS[0],
                    expected_revision=1,
                    final_status="completed",
                )
                self.assertEqual(released["status"], "released")
            receipts = list(
                (root / ".codex" / "coordination" / "archive").glob("*.json")
            )
            self.assertEqual(len(receipts), 2)
            self.assertNotEqual(receipts[0].name, receipts[1].name)

    def test_broken_current_view_never_blocks_canonical_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            current = root / ".codex" / "coordination" / "CURRENT.md"
            current.mkdir()

            claimed = _claim(root, 0, "src/a")
            self.assertEqual(claimed["status"], "claimed")
            self.assertEqual(state.list_board(root)["activeCount"], 1)
            self.assertTrue(current.is_dir())

            current.rmdir()
            _claim(root, 0, "src/b", expected_revision=1)
            rebuilt = current.read_text(encoding="utf-8")
            self.assertIn("path: src/b", rebuilt)
            self.assertNotIn("path: src/a", rebuilt)

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
                except Exception as error:  # surfaced below with its exact type
                    outcomes.append(type(error).__name__)

            threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertEqual(sorted(outcomes), ["claimed", "conflict"])
            self.assertEqual(state.list_board(root)["activeCount"], 1)

    def test_source_contains_no_ledger_inbox_or_transcript_reader(self) -> None:
        source = STATE_TOOL.read_text(encoding="utf-8")
        self.assertIn('CURRENT_VIEW_NAME = "CURRENT.md"', source)
        for forbidden in ("scan_inbox", "rollout", "sqlite", "transcript"):
            if forbidden == "transcript":
                self.assertIn("never reads or stores task\ntranscripts", source)
            else:
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
