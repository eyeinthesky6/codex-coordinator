from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
SCRIPTS = PLUGIN / "scripts"
HOOK = SCRIPTS / "codex_coordinator_session_start.py"


class PythonBootstrapTests(unittest.TestCase):
    def test_bootstraps_with_a_compatible_machine_python(self) -> None:
        payload = json.dumps(
            {
                "cwd": str(REPOSITORY),
                "session_id": "00000000-0000-0000-0000-000000000000",
            }
        )
        if os.name == "nt":
            command = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPTS / "codex_coordinator_bootstrap.ps1"),
                "-HookPath",
                str(HOOK),
                "-NoInstall",
            ]
        else:
            command = [
                "sh",
                str(SCRIPTS / "codex_coordinator_bootstrap.sh"),
                str(HOOK),
                "--no-install",
            ]

        environment = os.environ.copy()
        environment["CODEX_COORDINATOR_DISABLE_MISSION_CONTROL_AUTOSTART"] = "1"
        result = subprocess.run(
            command,
            input=payload,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
            env=environment,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            result.stdout.strip(),
            f"bootstrap produced no stdout; stderr={result.stderr!r}",
        )
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                f"bootstrap stdout was not JSON: {result.stdout!r}; "
                f"stderr={result.stderr!r}; error={error}"
            )
        self.assertTrue(output["continue"])
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_discovery_is_bounded_and_install_is_informed(self) -> None:
        powershell = (SCRIPTS / "codex_coordinator_bootstrap.ps1").read_text(encoding="utf-8")
        shell = (SCRIPTS / "codex_coordinator_bootstrap.sh").read_text(encoding="utf-8")

        self.assertIn("codex-runtimes", powershell)
        self.assertIn("codex-runtimes", shell)
        self.assertIn("Python 3.10+ was not found", powershell)
        self.assertIn("Python 3.10+ was not found", shell)
        self.assertIn("--scope user", powershell)
        self.assertNotIn("Get-ChildItem C:\\\\", powershell)
        self.assertNotIn("find / ", shell)
        self.assertNotIn("sudo", shell)


if __name__ == "__main__":
    unittest.main()
