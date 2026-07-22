from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
SCRIPT = PLUGIN / "scripts" / "codex_coordinator_session_start.py"


def _marker(*, enabled: str = "true", schema: str = "2") -> str:
    return "\n".join(
        [
            f"schema_version: {schema}",
            f"coordination_enabled: {enabled}",
            "project_id: sample",
            "canonical_paths:",
            "  active: .codex/coordination/active",
            "  archive: .codex/coordination/archive",
            "access:",
            "  cross_project_task_access: false",
            "  cross_project_state_changes: false",
            "",
        ]
    )


class SessionStartTests(unittest.TestCase):
    def _repository(self, directory: str, marker: str | None = None) -> Path:
        root = Path(directory)
        (root / ".git").mkdir()
        if marker is not None:
            path = root / ".codex" / "coordination" / "project.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(marker, encoding="utf-8")
        return root

    def _run(self, cwd: Path, payload: dict | None = None) -> tuple[int, str]:
        completed = subprocess.run(
            [sys.executable, "-I", str(SCRIPT)],
            input=json.dumps(payload if payload is not None else {"cwd": str(cwd)}),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.stderr, "")
        return completed.returncode, completed.stdout

    def test_absent_and_disabled_markers_are_silent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            self.assertEqual(self._run(root), (0, ""))
            path = root / ".codex" / "coordination" / "project.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(_marker(enabled="false"), encoding="utf-8")
            (path.parent / "active").mkdir()
            (path.parent / "active" / "broken.json").write_text("{broken", encoding="utf-8")
            self.assertEqual(self._run(root), (0, ""))

    def test_enabled_marker_emits_only_bounded_load_hint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, _marker())
            nested = root / "src" / "nested"
            nested.mkdir(parents=True)
            code, output = self._run(nested)
            report = json.loads(output)
        self.assertEqual(code, 0)
        context = report["hookSpecificOutput"]["additionalContext"]
        self.assertIn("project_id=sample", context)
        self.assertIn("grants no ownership", context)
        self.assertIn("launches no process", context)
        self.assertIn("stores no transcript", context)
        self.assertNotIn("CURRENT.md", context)
        self.assertNotIn("Mission Control", context)
        self.assertLess(len(context), 700)

    def test_legacy_or_ambiguous_enabled_marker_fails_closed(self) -> None:
        cases = {
            "legacy": _marker(schema="1"),
            "duplicate": _marker() + "coordination_enabled: true\n",
            "cross project": _marker().replace(
                "cross_project_task_access: false", "cross_project_task_access: true"
            ),
        }
        for name, marker in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = self._repository(directory, marker)
                code, output = self._run(root)
                context = json.loads(output)["hookSpecificOutput"]["additionalContext"]
                self.assertEqual(code, 0)
                self.assertIn("enabled but incompatible", context)
                self.assertIn("Do not change board claims", context)

    def test_oversized_marker_reports_incompatibility_without_reading_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, _marker() + ("# padding\n" * 3000))
            code, output = self._run(root)
            context = json.loads(output)["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(code, 0)
        self.assertIn("hook_validation_failed", context)

    def test_invalid_hook_input_is_quiet(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", str(SCRIPT)],
            input="not json",
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")

    def test_packaged_hook_is_direct_bounded_and_has_no_runtime_launcher(self) -> None:
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        command = hooks["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertEqual(command["timeout"], 5)
        self.assertIn("codex_coordinator_session_start.py", command["command"])
        self.assertIn("codex_coordinator_session_start.py", command["commandWindows"])
        self.assertNotIn("bootstrap", json.dumps(command).casefold())
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("subprocess", "mission_control", "sqlite", "rollout", "CURRENT.md"):
            self.assertNotIn(forbidden, source)
        self.assertFalse((PLUGIN / "scripts" / "codex_coordinator_bootstrap.ps1").exists())
        self.assertFalse((PLUGIN / "scripts" / "codex_coordinator_bootstrap.sh").exists())


if __name__ == "__main__":
    unittest.main()
