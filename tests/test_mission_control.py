from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
SKILL = PLUGIN / "skills" / "codex-coordinator"
MISSION_CONTROL = PLUGIN / "mission_control" / "mission_control.py"
LIFECYCLE = PLUGIN / "scripts" / "codex_coordinator_project.py"
STATE = SKILL / "scripts" / "coordination_state.py"


class MissionControlIsolationTests(unittest.TestCase):
    def test_legacy_observer_runtime_is_not_shipped(self) -> None:
        self.assertTrue(MISSION_CONTROL.is_file())
        self.assertTrue((PLUGIN / "mission_control" / "README.md").is_file())
        shipped_names = {
            path.name for path in (PLUGIN / "mission_control").rglob("*") if path.is_file()
        }
        for legacy in ("collector.py", "server.py", "start-background.ps1", "stop.ps1"):
            self.assertNotIn(legacy, shipped_names)
        self.assertFalse((REPOSITORY / "apps" / "mission_control").exists())
        self.assertFalse((PLUGIN / "scripts" / "mission_control_lifecycle.py").exists())
        self.assertFalse((REPOSITORY / "tests" / "verify_mission_control_ui.py").exists())

    def test_legacy_observer_is_not_imported_by_base_runtime(self) -> None:
        base_files = (
            PLUGIN / "scripts" / "codex_coordinator_session_start.py",
            PLUGIN / "scripts" / "codex_coordinator_doctor.py",
            PLUGIN / "scripts" / "codex_coordinator_project.py",
            SKILL / "scripts" / "coordination_state.py",
        )
        content = "\n".join(path.read_text(encoding="utf-8") for path in base_files).casefold()
        self.assertNotIn("import mission_control", content)
        self.assertNotIn("mission_control_lifecycle", content)
        self.assertNotIn("start-background", content)

    def test_base_metadata_describes_only_the_optional_read_only_dashboard(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        metadata = json.dumps(manifest).casefold()
        self.assertIn("mission control", metadata)
        self.assertIn("optional", metadata)
        self.assertIn("read-only", metadata)
        self.assertNotIn("run doctor across", metadata)

    def test_optional_observer_renders_active_board_without_polling_or_controls(self) -> None:
        spec = importlib.util.spec_from_file_location("mission_control_test", MISSION_CONTROL)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            initialized = subprocess.run(
                [
                    sys.executable,
                    str(LIFECYCLE),
                    "project",
                    "init",
                    "--project-root",
                    str(root),
                    "--project-id",
                    "mission-sample",
                    "--project-name",
                    "Mission Sample",
                    "--task-prefix",
                    "MS",
                    "--apply",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            claimed = subprocess.run(
                [
                    sys.executable,
                    str(STATE),
                    "claim",
                    "--project-root",
                    str(root),
                    "--thread-id",
                    "11111111-1111-4111-8111-111111111111",
                    "--title",
                    "Release checks",
                    "--goal",
                    "Verify the public release",
                    "--path",
                    "docs",
                    "--expected-revision",
                    "0",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(claimed.returncode, 0, claimed.stderr)
            rendered = module.render_dashboard(module.read_board(root), root).decode("utf-8")

        self.assertIn("Mission Control", rendered)
        self.assertIn("Release checks", rendered)
        self.assertIn("Verify the public release", rendered)
        self.assertIn("Read-only local view", rendered)
        self.assertNotIn("setInterval", rendered)
        self.assertNotIn("fetch(", rendered)
        self.assertNotIn("Stop task", rendered)
        self.assertNotIn("Send message", rendered)

    def test_supported_board_contract_has_no_private_native_state_fields(self) -> None:
        state = (SKILL / "scripts" / "coordination_state.py").read_text(encoding="utf-8").casefold()
        for forbidden in (
            "state_*.sqlite",
            "rollout",
            "task transcript",
            "tool output",
            "provider response",
        ):
            if forbidden in {"task transcript", "tool output"}:
                continue
            self.assertNotIn(forbidden, state)
        self.assertIn("never reads or stores task transcripts", " ".join(state.split()))
        for legacy_field in (
            "coordination epoch",
            "pending commands",
            "resume queue",
            "turn_reconciliation",
        ):
            self.assertNotIn(legacy_field, state)

    def test_optional_observer_has_no_task_authority_in_guidance(self) -> None:
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("manually started for one explicit project", skill)
        self.assertIn("has no task authority", skill)
        self.assertIn("Optional observers are not part of the core path", skill)


if __name__ == "__main__":
    unittest.main()
