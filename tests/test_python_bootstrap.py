from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


class PythonBootstrapTests(unittest.TestCase):
    def test_session_start_uses_existing_python_and_has_no_bootstrap_scripts(self) -> None:
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        hook = hooks["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertEqual(hook["timeout"], 5)
        self.assertTrue(hook["command"].startswith("python3 -I"))
        self.assertTrue(hook["commandWindows"].startswith("python -I"))
        self.assertFalse((PLUGIN / "scripts" / "codex_coordinator_bootstrap.ps1").exists())
        self.assertFalse((PLUGIN / "scripts" / "codex_coordinator_bootstrap.sh").exists())

    def test_core_scripts_do_not_install_python_or_mutate_path(self) -> None:
        scripts = (
            PLUGIN / "scripts" / "codex_coordinator_session_start.py",
            PLUGIN / "scripts" / "codex_coordinator_doctor.py",
        )
        forbidden = (
            "winget",
            "apt-get",
            "brew install",
            "dnf install",
            "yum install",
            "pacman",
            "choco",
            "setx path",
            "environmentvariabletarget",
            "subprocess",
        )
        for script in scripts:
            source = script.read_text(encoding="utf-8").casefold()
            for token in forbidden:
                self.assertNotIn(token, source, f"{token} found in {script.name}")


if __name__ == "__main__":
    unittest.main()
