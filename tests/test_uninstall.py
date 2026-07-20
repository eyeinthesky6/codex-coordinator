from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "plugins" / "codex-coordinator" / "scripts" / "codex_coordinator_uninstall.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("codex_coordinator_uninstall", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load uninstall module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


uninstall = _load_module()


class UninstallTests(unittest.TestCase):
    def _project(self, base: Path, *, project_id: str = "sample", enabled: bool = True) -> Path:
        root = base / project_id
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=10)
        coordination = root / ".codex" / "coordination"
        coordination.mkdir(parents=True)
        (coordination / "project.yaml").write_text(
            "schema_version: 1\n"
            f"coordination_enabled: {'true' if enabled else 'false'}\n"
            f"project_id: {project_id}\n"
            f"project_name: {project_id.title()}\n"
            "task_prefix: SAMPLE\n",
            encoding="utf-8",
        )
        (coordination / "CURRENT.md").write_text(
            "**Coordinator thread ID:** 11111111-1111-4111-8111-111111111111\n",
            encoding="utf-8",
        )
        (coordination / "history.txt").write_text("preserve me\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(
            "# Existing instructions\n\nKeep this line.\n\n" + uninstall.DISCOVERY_BLOCK + "\n",
            encoding="utf-8",
        )
        (root / ".gitignore").write_text(
            "node_modules/\n\n" + uninstall.IGNORE_BLOCK + "\n\nkeep.me\n",
            encoding="utf-8",
        )
        return root

    def _run(self, *arguments: str) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = uninstall.main(list(arguments))
        return code, json.loads(output.getvalue())

    def test_deactivate_is_dry_run_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            marker = root / ".codex" / "coordination" / "project.yaml"
            agents = root / "AGENTS.md"
            before = (marker.read_bytes(), agents.read_bytes())

            code, result = self._run("project", "deactivate", "--project-root", str(root))

            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "planned")
            self.assertEqual((marker.read_bytes(), agents.read_bytes()), before)
            self.assertEqual(result["projectId"], "sample")
            self.assertIn("remove-repository-heartbeat", str(result["requiredNativeActions"]))

    def test_deactivate_and_reactivate_preserve_history_and_unrelated_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            history = root / ".codex" / "coordination" / "history.txt"
            ignore = root / ".gitignore"
            ignore_before = ignore.read_bytes()

            code, first = self._run("project", "deactivate", "--project-root", str(root), "--apply")
            self.assertEqual(code, 0, first)
            self.assertIn("coordination_enabled: false", (root / ".codex" / "coordination" / "project.yaml").read_text())
            self.assertNotIn(uninstall.DISCOVERY_BLOCK, (root / "AGENTS.md").read_text())
            self.assertIn("Keep this line.", (root / "AGENTS.md").read_text())
            self.assertEqual(history.read_text(encoding="utf-8"), "preserve me\n")
            self.assertEqual(ignore.read_bytes(), ignore_before)

            code, repeat = self._run("project", "deactivate", "--project-root", str(root), "--apply")
            self.assertEqual(code, 0, repeat)
            self.assertEqual(repeat["actions"], [])

            code, restored = self._run("project", "reactivate", "--project-root", str(root), "--apply")
            self.assertEqual(code, 0, restored)
            self.assertIn("coordination_enabled: true", (root / ".codex" / "coordination" / "project.yaml").read_text())
            self.assertEqual((root / "AGENTS.md").read_text().count(uninstall.DISCOVERY_BLOCK), 1)

    def test_changed_discovery_block_stops_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            agents = root / "AGENTS.md"
            agents.write_text("# Existing\n\n## Codex Coordinator\n\nDifferent text.\n", encoding="utf-8")
            marker = root / ".codex" / "coordination" / "project.yaml"
            before = marker.read_bytes()

            code, result = self._run("project", "deactivate", "--project-root", str(root), "--apply")

            self.assertEqual(code, 2)
            self.assertIn("differs", result["error"])
            self.assertEqual(marker.read_bytes(), before)

    def test_exact_legacy_discovery_block_can_deactivate_and_reactivate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8").replace(
                    uninstall.DISCOVERY_BLOCK, uninstall.LEGACY_DISCOVERY_BLOCKS[0]
                ),
                encoding="utf-8",
            )

            code, disabled = self._run(
                "project", "deactivate", "--project-root", str(root), "--apply"
            )
            self.assertEqual(code, 0, disabled)
            self.assertNotIn("## Codex Coordinator", agents.read_text(encoding="utf-8"))

            code, enabled = self._run(
                "project", "reactivate", "--project-root", str(root), "--apply"
            )
            self.assertEqual(code, 0, enabled)
            self.assertEqual(agents.read_text(encoding="utf-8").count(uninstall.DISCOVERY_BLOCK), 1)
            self.assertNotIn(uninstall.LEGACY_DISCOVERY_BLOCKS[0], agents.read_text(encoding="utf-8"))

    def test_malformed_marker_stops_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            marker = root / ".codex" / "coordination" / "project.yaml"
            marker.write_text(
                marker.read_text(encoding="utf-8") + "coordination_enabled: false\n",
                encoding="utf-8",
            )
            agents = root / "AGENTS.md"
            before = agents.read_bytes()

            code, result = self._run(
                "project", "deactivate", "--project-root", str(root), "--apply"
            )

            self.assertEqual(code, 2)
            self.assertIn("exactly one coordination_enabled", result["error"])
            self.assertEqual(agents.read_bytes(), before)

    def test_project_purge_requires_exact_confirmation_and_preserves_unrelated_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            unrelated = root / ".codex" / "config.toml"
            unrelated.write_text('model = "example"\n', encoding="utf-8")

            code, rejected = self._run("project", "purge", "--project-root", str(root), "--apply")
            self.assertEqual(code, 2)
            self.assertIn("confirm-project-id", rejected["error"])
            self.assertTrue((root / ".codex" / "coordination").exists())

            code, result = self._run(
                "project",
                "purge",
                "--project-root",
                str(root),
                "--confirm-project-id",
                "sample",
                "--apply",
            )
            self.assertEqual(code, 0, result)
            self.assertFalse((root / ".codex" / "coordination").exists())
            self.assertEqual(unrelated.read_text(encoding="utf-8"), 'model = "example"\n')
            self.assertIn("node_modules/", (root / ".gitignore").read_text())
            self.assertIn("keep.me", (root / ".gitignore").read_text())
            self.assertNotIn(uninstall.IGNORE_BLOCK, (root / ".gitignore").read_text())
            self.assertIn("Keep this line.", (root / "AGENTS.md").read_text())

    def test_document_batch_rolls_back_after_a_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            marker_path = root / ".codex" / "coordination" / "project.yaml"
            agents_path = root / "AGENTS.md"
            before = (marker_path.read_bytes(), agents_path.read_bytes())
            real_write = uninstall._atomic_write
            calls = 0

            def fail_once(path: Path, payload: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated interruption")
                real_write(path, payload)

            with mock.patch.object(uninstall, "_atomic_write", side_effect=fail_once):
                code, result = self._run("project", "deactivate", "--project-root", str(root), "--apply")

            self.assertEqual(code, 2)
            self.assertIn("simulated interruption", result["error"])
            self.assertEqual((marker_path.read_bytes(), agents_path.read_bytes()), before)

    def test_interrupted_purge_resumes_from_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._project(Path(directory))
            real_remove = uninstall.shutil.rmtree

            with mock.patch.object(
                uninstall.shutil, "rmtree", side_effect=OSError("simulated purge interruption")
            ):
                code, interrupted = self._run(
                    "project",
                    "purge",
                    "--project-root",
                    str(root),
                    "--confirm-project-id",
                    "sample",
                    "--apply",
                )

            self.assertEqual(code, 2)
            self.assertIn("simulated purge interruption", interrupted["error"])
            quarantine = root / ".codex" / uninstall.QUARANTINE_NAME
            self.assertFalse((root / ".codex" / "coordination").exists())
            self.assertTrue(quarantine.exists())

            with mock.patch.object(uninstall.shutil, "rmtree", side_effect=real_remove):
                code, resumed = self._run(
                    "project",
                    "purge",
                    "--project-root",
                    str(root),
                    "--confirm-project-id",
                    "sample",
                    "--apply",
                )

            self.assertEqual(code, 0, resumed)
            self.assertFalse(quarantine.exists())

    def test_index_and_global_plan_verify_every_project_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = self._project(base)
            codex_home = base / "codex-home"
            unrelated = codex_home / "automations" / "unrelated" / "automation.toml"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text('name = "Unrelated"\n', encoding="utf-8")
            unrelated_before = unrelated.read_bytes()

            code, indexed = self._run(
                "index-project",
                "--project-root",
                str(root),
                "--codex-home",
                str(codex_home),
                "--apply",
            )
            self.assertEqual(code, 0, indexed)
            code, plan = self._run("global-plan", "--codex-home", str(codex_home))
            self.assertEqual(code, 0, plan)
            self.assertEqual(len(plan["verifiedProjects"]), 1)
            self.assertEqual(plan["rejectedProjects"], [])
            self.assertTrue(plan["projectHistoryPreserved"])
            self.assertEqual(unrelated.read_bytes(), unrelated_before)

            index_path = codex_home / "codex-coordinator" / "projects.json"
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            payload["projects"][0]["projectId"] = "wrong-project"
            index_path.write_text(json.dumps(payload), encoding="utf-8")
            code, rejected = self._run("global-plan", "--codex-home", str(codex_home))
            self.assertEqual(code, 0, rejected)
            self.assertEqual(rejected["verifiedProjects"], [])
            self.assertIn("does not match", rejected["rejectedProjects"][0]["reason"])

    def test_script_has_no_drive_scan_or_implicit_global_mutation(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("Get-ChildItem C:\\\\", source)
        self.assertNotIn("os.walk(\"/\")", source)
        self.assertNotIn("subprocess.run([\"codex\"", source)
        self.assertIn('"global-plan"', source)
        self.assertIn('"--apply"', source)


if __name__ == "__main__":
    unittest.main()
