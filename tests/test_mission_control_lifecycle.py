from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


class MissionControlLifecycleRetirementTests(unittest.TestCase):
    def test_session_start_never_starts_or_opens_mission_control(self) -> None:
        hook = (PLUGIN / "scripts" / "codex_coordinator_session_start.py").read_text(encoding="utf-8").casefold()
        registration = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertNotIn("mission_control", hook)
        self.assertNotIn("subprocess", hook)
        self.assertNotIn("browser", hook)
        self.assertNotIn("mission", json.dumps(registration).casefold())

    def test_core_contract_has_no_observer_lifecycle(self) -> None:
        contract = json.loads(
            (PLUGIN / "skills" / "codex-coordinator" / "capabilities.json").read_text(encoding="utf-8")
        )["capabilities"]
        self.assertEqual(
            contract["missionControl"], "not-shipped-separate-package-only"
        )
        for removed in ("missionControlLifecycle", "missionControlDoctor", "monitoring"):
            self.assertNotIn(removed, contract)


if __name__ == "__main__":
    unittest.main()
