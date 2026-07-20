from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
LIFECYCLE = (
    REPOSITORY
    / "plugins"
    / "codex-coordinator"
    / "scripts"
    / "mission_control_lifecycle.py"
)


def _load_lifecycle():
    name = "mission_control_lifecycle_test_module"
    spec = importlib.util.spec_from_file_location(name, LIFECYCLE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Mission Control lifecycle module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class MissionControlLifecycleTests(unittest.TestCase):
    def test_spawn_uses_exact_isolated_package_and_ignores_json_shadows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "plugin"
            scripts = plugin / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(LIFECYCLE, scripts / LIFECYCLE.name)
            shutil.copytree(
                REPOSITORY / "plugins" / "codex-coordinator" / "mission_control",
                plugin / "mission_control",
            )
            marker = root / "shadow-executed.txt"
            shadow = (
                "import os\n"
                "open(os.environ['CODEX_SHADOW_MARKER'], 'w', encoding='utf-8').write(__file__)\n"
                "raise RuntimeError('shadow json executed')\n"
            )
            (scripts / "json.py").write_text(shadow, encoding="utf-8")
            (plugin / "json.py").write_text(shadow, encoding="utf-8")
            spec = importlib.util.spec_from_file_location(
                "isolated_lifecycle_fixture", scripts / LIFECYCLE.name
            )
            assert spec and spec.loader
            lifecycle = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lifecycle)

            with mock.patch.object(lifecycle.subprocess, "Popen") as popen:
                lifecycle._spawn(REPOSITORY, 4317, open_browser=False)

            command = popen.call_args.args[0]
            self.assertEqual(command[:3], [sys.executable, "-I", "-c"])
            self.assertEqual(Path(command[4]), (plugin / "mission_control").resolve())
            self.assertEqual(command[-1], "--no-open")
            environment = os.environ.copy()
            environment["CODEX_SHADOW_MARKER"] = str(marker)
            environment["PYTHONPATH"] = str(plugin)
            completed = subprocess.run(
                [*command[:5], "--help"],
                cwd=plugin,
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
                env=environment,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(marker.exists(), completed.stderr)

    def setUp(self) -> None:
        self.lifecycle = _load_lifecycle()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state_path = Path(self.temporary.name) / "lifecycle.json"
        self.path_patch = mock.patch.object(
            self.lifecycle, "_lifecycle_path", return_value=self.state_path
        )
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)

    def test_first_automatic_start_opens_once_and_later_sessions_reuse(self) -> None:
        with (
            mock.patch.object(
                self.lifecycle, "_health", side_effect=[False, True, True]
            ),
            mock.patch.object(self.lifecycle, "_spawn") as spawn,
        ):
            result = self.lifecycle.start(
                REPOSITORY, 4317, automatic=True, open_browser=False
            )
            reused = self.lifecycle.start(
                REPOSITORY, 4317, automatic=True, open_browser=False
            )

        self.assertEqual(result, "started")
        self.assertEqual(reused, "running")
        spawn.assert_called_once_with(REPOSITORY, 4317, open_browser=True)
        state = self.lifecycle._read_lifecycle()
        self.assertTrue(state["automatic_start_enabled"])
        self.assertTrue(state["browser_opened"])

    def test_stop_disables_future_automatic_start(self) -> None:
        self.lifecycle._write_lifecycle(enabled=True, browser_opened=True)
        with (
            mock.patch.object(self.lifecycle, "_shutdown", return_value=True),
            mock.patch.object(self.lifecycle, "_health", side_effect=[False, True]),
        ):
            self.assertEqual(self.lifecycle.stop(4317), "stopped")
        with mock.patch.object(self.lifecycle, "_spawn") as spawn:
            self.assertEqual(
                self.lifecycle.start(
                    REPOSITORY, 4317, automatic=True, open_browser=False
                ),
                "disabled",
            )
        spawn.assert_not_called()
        self.assertFalse(
            self.lifecycle._read_lifecycle()["automatic_start_enabled"]
        )

    def test_chat_start_reenables_after_shutdown(self) -> None:
        self.lifecycle._write_lifecycle(enabled=False, browser_opened=True)
        with (
            mock.patch.object(self.lifecycle, "_health", side_effect=[False, True]),
            mock.patch.object(self.lifecycle, "_spawn") as spawn,
        ):
            result = self.lifecycle.start(
                REPOSITORY, 4317, automatic=False, open_browser=True
            )
        self.assertEqual(result, "started")
        spawn.assert_called_once_with(REPOSITORY, 4317, open_browser=True)
        self.assertTrue(
            self.lifecycle._read_lifecycle()["automatic_start_enabled"]
        )


if __name__ == "__main__":
    unittest.main()
