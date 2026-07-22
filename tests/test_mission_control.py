from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
SKILL = PLUGIN / "skills" / "codex-coordinator"


class MissionControlIsolationTests(unittest.TestCase):
    def test_legacy_observer_runtime_is_not_shipped(self) -> None:
        for root in (
            PLUGIN / "mission_control",
            REPOSITORY / "apps" / "mission_control",
        ):
            shipped_files = [
                path
                for path in root.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            ]
            self.assertEqual(shipped_files, [])
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

    def test_base_metadata_does_not_advertise_dashboard_or_doctor_scan(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        metadata = json.dumps(manifest).casefold()
        self.assertNotIn("start mission control", metadata)
        self.assertNotIn("run doctor across", metadata)
        self.assertNotIn("dashboard", metadata)

    def test_supported_board_contract_has_no_private_native_state_fields(self) -> None:
        state = (SKILL / "scripts" / "coordination_state.py").read_text(encoding="utf-8").casefold()
        for forbidden in (
            "state_*.sqlite",
            "rollout",
            "task transcript",
            "tool output",
            "provider response",
            "current.md",
        ):
            if forbidden in {"task transcript", "tool output"}:
                continue
            self.assertNotIn(forbidden, state)
        self.assertIn("never reads or\nstores task transcripts", state)

    def test_optional_observer_has_no_task_authority_in_guidance(self) -> None:
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("manually started, read-only, and has no task authority", skill)
        self.assertIn("Mission Control is not part of the core path", skill)


if __name__ == "__main__":
    unittest.main()
