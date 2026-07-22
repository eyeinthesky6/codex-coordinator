from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


class DoctorScannerRetirementTests(unittest.TestCase):
    def test_project_scanner_is_not_reachable_from_core(self) -> None:
        core_paths = (
            PLUGIN / "scripts" / "codex_coordinator_doctor.py",
            PLUGIN / "scripts" / "codex_coordinator_session_start.py",
            PLUGIN / "hooks" / "hooks.json",
            PLUGIN / "skills" / "codex-coordinator" / "SKILL.md",
            PLUGIN / "skills" / "codex-coordinator" / "scripts" / "coordination_state.py",
        )
        content = "\n".join(path.read_text(encoding="utf-8") for path in core_paths).casefold()
        for forbidden in (
            "doctor_scan",
            "deterministicdoctorscanner",
            "write_findings",
            "deep review",
            "semantic packet",
        ):
            self.assertNotIn(forbidden, content)

    def test_retired_scanner_is_not_a_packaged_contract_dependency(self) -> None:
        doctor = (PLUGIN / "scripts" / "codex_coordinator_doctor.py").read_text(encoding="utf-8")
        contract = (PLUGIN / "skills" / "codex-coordinator" / "capabilities.json").read_text(encoding="utf-8")
        self.assertNotIn("mission_control", doctor)
        self.assertNotIn("doctorProjectScan", contract)
        self.assertNotIn("doctorSemanticReview", contract)


if __name__ == "__main__":
    unittest.main()
