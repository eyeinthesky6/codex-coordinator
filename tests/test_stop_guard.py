from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
SCRIPT = PLUGIN / "scripts" / "codex_coordinator_stop_guard.py"
THREAD = "11111111-2222-4333-8444-555555555555"
OTHER_THREAD = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def _marker(*, enabled: str = "true", project_id: str = "sample") -> str:
    return "\n".join(
        [
            "schema_version: 2",
            f"coordination_enabled: {enabled}",
            f"project_id: {project_id}",
            "canonical_paths:",
            "  active: .codex/coordination/active",
            "  archive: .codex/coordination/archive",
            "access:",
            "  cross_project_task_access: false",
            "  cross_project_state_changes: false",
            "",
        ]
    )


def _claim(thread_id: str = THREAD, *, status: str = "active", revision: int = 3) -> dict:
    return {
        "schemaVersion": 1,
        "projectId": "sample",
        "threadId": thread_id,
        "title": "Bounded work",
        "goal": "Prove lifecycle cleanup",
        "status": status,
        "revision": revision,
        "createdAt": "2026-07-22T00:00:00Z",
        "updatedAt": "2026-07-22T00:01:00Z",
        "paths": ["src"],
        "actions": [],
        "blockedBy": [],
        "limitOverride": False,
    }


class StopGuardTests(unittest.TestCase):
    def _repository(self, directory: str, *, enabled: str = "true") -> Path:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        (root / ".git").mkdir()
        marker = root / ".codex" / "coordination" / "project.yaml"
        marker.parent.mkdir(parents=True)
        marker.write_text(_marker(enabled=enabled), encoding="utf-8")
        (marker.parent / "active").mkdir()
        return root

    def _write_claim(self, root: Path, value: dict) -> None:
        path = root / ".codex" / "coordination" / "active" / f"{value['threadId']}.json"
        path.write_text(json.dumps(value), encoding="utf-8")

    def _run(self, root: Path, **changes) -> tuple[int, str]:
        payload = {
            "hook_event_name": "Stop",
            "session_id": THREAD,
            "cwd": str(root),
            "stop_hook_active": False,
            "transcript_path": str(root / "private-transcript.jsonl"),
            "last_assistant_message": "PRIVATE ASSISTANT TEXT",
        }
        payload.update(changes)
        completed = subprocess.run(
            [sys.executable, "-I", str(SCRIPT)],
            input=json.dumps(payload),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.stderr, "")
        return completed.returncode, completed.stdout

    def test_absent_disabled_and_unowned_projects_are_silent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, enabled="false")
            self._write_claim(root, _claim())
            self.assertEqual(self._run(root), (0, ""))
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            self.assertEqual(self._run(root), (0, ""))
            self._write_claim(root, _claim(OTHER_THREAD))
            self.assertEqual(self._run(root), (0, ""))

    def test_active_own_claim_requests_one_bounded_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            self._write_claim(root, _claim())
            code, output = self._run(root)
        self.assertEqual(code, 0)
        value = json.loads(output)
        self.assertEqual(value["decision"], "block")
        self.assertIn("revision 3", value["reason"])
        self.assertIn("release", value["reason"])
        self.assertNotIn("PRIVATE", output)
        self.assertNotIn(str(root), output)

    def test_blocked_claim_and_guard_continuation_are_silent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            self._write_claim(root, _claim(status="blocked"))
            self.assertEqual(self._run(root), (0, ""))
            self._write_claim(root, _claim(status="active"))
            self.assertEqual(self._run(root, stop_hook_active=True), (0, ""))

    def test_malformed_exact_claim_fails_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            path = root / ".codex" / "coordination" / "active" / f"{THREAD}.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(self._run(root), (0, ""))

    def test_linked_worktree_uses_primary_board_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            primary = base / "primary"
            linked = base / "linked"
            self._repository(str(primary))
            linked.mkdir()
            linked_marker = linked / ".codex" / "coordination" / "project.yaml"
            linked_marker.parent.mkdir(parents=True)
            linked_marker.write_text(_marker(), encoding="utf-8")
            git_dir = primary / ".git" / "worktrees" / "linked"
            git_dir.mkdir(parents=True)
            (git_dir / "commondir").write_text("../..\n", encoding="utf-8")
            (linked / ".git").write_text(f"gitdir: {git_dir}\n", encoding="utf-8")
            self._write_claim(primary, _claim(revision=4))
            code, output = self._run(linked)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["decision"], "block")
        self.assertIn("revision 4", output)

    def test_packaged_stop_hook_is_bounded_and_has_no_matcher(self) -> None:
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entry = hooks["hooks"]["Stop"][0]
        self.assertEqual(set(entry), {"hooks"})
        command = entry["hooks"][0]
        self.assertEqual(command["timeout"], 5)
        self.assertIn("codex_coordinator_stop_guard.py", command["command"])
        source = SCRIPT.read_text(encoding="utf-8").casefold()
        for forbidden in (
            "transcript_path",
            "last_assistant_message",
            "state_*.sqlite",
            "read_thread",
            "wait_threads",
            "subprocess",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
