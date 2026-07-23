from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


class BoundaryWorkflowTests(unittest.TestCase):
    def _json_command(self, script: Path, *args: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, str(script), *args],
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(completed.stderr, "")
        return completed.returncode, json.loads(completed.stdout)

    def test_isolated_package_runs_one_complete_boundary_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            package = temporary / "installed-plugin"
            shutil.copytree(
                PLUGIN,
                package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            lifecycle = package / "scripts" / "codex_coordinator_project.py"
            state = (
                package
                / "skills"
                / "codex-coordinator"
                / "scripts"
                / "coordination_state.py"
            )
            doctor = package / "scripts" / "codex_coordinator_doctor.py"
            hook = package / "scripts" / "codex_coordinator_session_start.py"
            stop_guard = package / "scripts" / "codex_coordinator_stop_guard.py"
            root = temporary / "project"
            root.mkdir()
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)

            code, health = self._json_command(doctor, "--check")
            self.assertEqual(code, 0)
            self.assertEqual(health["status"], "healthy")

            code, initialized = self._json_command(
                lifecycle,
                "project",
                "init",
                "--project-root",
                str(root),
                "--project-id",
                "workflow-sample",
                "--project-name",
                "Workflow Sample",
                "--task-prefix",
                "WF",
                "--apply",
            )
            self.assertEqual(code, 0)
            self.assertEqual(initialized["activeClaimsCreated"], 0)
            self.assertEqual(initialized["nativeTasksCreated"], 0)
            self.assertEqual(initialized["backgroundProcessesCreated"], 0)

            hook_run = subprocess.run(
                [sys.executable, str(hook)],
                input=json.dumps({"cwd": str(root)}),
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(hook_run.returncode, 0)
            self.assertIn("task-boundary board", hook_run.stdout)

            code, empty = self._json_command(
                state, "list", "--project-root", str(root)
            )
            self.assertEqual(code, 0)
            self.assertEqual(empty["activeCount"], 0)

            first = "11111111-1111-4111-8111-111111111111"
            second = "22222222-2222-4222-8222-222222222222"
            conflicting = "33333333-3333-4333-8333-333333333333"
            code, claimed = self._json_command(
                state,
                "claim",
                "--project-root",
                str(root),
                "--thread-id",
                first,
                "--title",
                "Documentation",
                "--goal",
                "Update bounded documentation",
                "--path",
                "docs",
                "--action",
                "git-integration",
                "--expected-revision",
                "0",
            )
            self.assertEqual(code, 0)
            self.assertEqual(claimed["status"], "claimed")
            current = root / ".codex" / "coordination" / "CURRENT.md"
            current_text = current.read_text(encoding="utf-8")
            self.assertIn("Active lanes: 1", current_text)
            self.assertIn(first, current_text)
            self.assertIn("git-integration", current_text)
            ignored = subprocess.run(
                ["git", "check-ignore", "--quiet", ".codex/coordination/CURRENT.md"],
                cwd=root,
                timeout=10,
                check=False,
            )
            self.assertEqual(ignored.returncode, 0)

            stop_run = subprocess.run(
                [sys.executable, "-I", str(stop_guard)],
                input=json.dumps(
                    {
                        "hook_event_name": "Stop",
                        "session_id": first,
                        "cwd": str(root),
                        "stop_hook_active": False,
                        "transcript_path": str(root / "private.jsonl"),
                    }
                ),
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(stop_run.returncode, 0)
            self.assertEqual(json.loads(stop_run.stdout)["decision"], "block")
            continued_stop = subprocess.run(
                [sys.executable, "-I", str(stop_guard)],
                input=json.dumps(
                    {
                        "hook_event_name": "Stop",
                        "session_id": first,
                        "cwd": str(root),
                        "stop_hook_active": True,
                    }
                ),
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(continued_stop.returncode, 0)
            self.assertEqual(continued_stop.stdout, "")

            code, disjoint = self._json_command(
                state,
                "claim",
                "--project-root",
                str(root),
                "--thread-id",
                second,
                "--title",
                "Source",
                "--goal",
                "Update bounded source",
                "--path",
                "src",
                "--expected-revision",
                "0",
            )
            self.assertEqual(code, 0)
            self.assertEqual(disjoint["activeCount"], 2)
            self.assertIn("Active lanes: 2", current.read_text(encoding="utf-8"))

            code, overlap = self._json_command(
                state,
                "claim",
                "--project-root",
                str(root),
                "--thread-id",
                conflicting,
                "--title",
                "Overlap",
                "--goal",
                "Attempt an overlapping documentation update",
                "--path",
                "docs/guide.md",
                "--expected-revision",
                "0",
            )
            self.assertEqual(code, 0)
            self.assertEqual(overlap["status"], "claimed")
            self.assertEqual(overlap["activeCount"], 3)
            self.assertEqual(overlap["warnings"][0]["threadId"], first)

            for thread_id in (first, second, conflicting):
                code, released = self._json_command(
                    state,
                    "release",
                    "--project-root",
                    str(root),
                    "--thread-id",
                    thread_id,
                    "--expected-revision",
                    "1",
                    "--status",
                    "completed",
                )
                self.assertEqual(code, 0)
                self.assertEqual(released["status"], "released")

            code, completed = self._json_command(
                state, "list", "--project-root", str(root)
            )
            self.assertEqual(code, 0)
            self.assertEqual(completed["activeCount"], 0)
            completed_view = current.read_text(encoding="utf-8")
            self.assertIn("Active lanes: 0", completed_view)
            self.assertNotIn(first, completed_view)
            self.assertNotIn(second, completed_view)
            receipts = list(
                (root / ".codex" / "coordination" / "archive").glob("*.json")
            )
            self.assertEqual(len(receipts), 3)

            code, disabled = self._json_command(
                lifecycle,
                "project",
                "deactivate",
                "--project-root",
                str(root),
                "--apply",
            )
            self.assertEqual(code, 0)
            self.assertEqual(disabled["requiredNativeActions"], [])
            marker = (root / ".codex" / "coordination" / "project.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("coordination_enabled: false", marker)
            code, unavailable = self._json_command(
                state, "list", "--project-root", str(root)
            )
            self.assertEqual(code, 1)
            self.assertIn("disabled", unavailable["error"])
            self.assertTrue(current.is_file())
            for legacy in ("tasks", "inbox"):
                self.assertFalse((root / ".codex" / "coordination" / legacy).exists())


if __name__ == "__main__":
    unittest.main()
