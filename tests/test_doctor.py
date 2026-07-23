from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
DOCTOR = PLUGIN / "scripts" / "codex_coordinator_doctor.py"


def _digest_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


class DoctorTests(unittest.TestCase):
    def _copy_plugin(self, directory: str) -> Path:
        target = Path(directory) / "plugin"
        shutil.copytree(PLUGIN, target)
        return target

    def _run(self, root: Path, *extra: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, str(DOCTOR), "--plugin-root", str(root), *extra],
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(completed.stderr, "")
        return completed.returncode, json.loads(completed.stdout)

    def test_packaged_plugin_is_healthy(self) -> None:
        code, report = self._run(PLUGIN, "--check")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["checks"], 6)
        self.assertEqual(report["failures"], 0)
        self.assertEqual(report["recommendedAction"], "none")

    def test_contract_drift_is_broken_and_reinstall_is_the_only_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_plugin(directory)
            path = root / "skills" / "codex-coordinator" / "capabilities.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["contractVersion"] = 19
            path.write_text(json.dumps(value), encoding="utf-8")
            code, report = self._run(root, "--check")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "broken")
        self.assertEqual(report["recommendedAction"], "update_or_reinstall")
        self.assertIn("Update or reinstall", report["message"])

    def test_duplicate_json_missing_skill_link_and_bootstrap_hook_fail(self) -> None:
        mutations = {
            "duplicate json": lambda root: (root / ".codex-plugin" / "plugin.json").write_text(
                '{"name":"codex-coordinator","name":"other","version":"0.3.0"}', encoding="utf-8"
            ),
            "missing link": lambda root: (root / "skills" / "codex-coordinator" / "SKILL.md").write_text(
                (root / "skills" / "codex-coordinator" / "SKILL.md").read_text(encoding="utf-8")
                + "\n[missing](references/missing.md)\n",
                encoding="utf-8",
            ),
            "bootstrap hook": lambda root: (root / "hooks" / "hooks.json").write_text(
                (root / "hooks" / "hooks.json").read_text(encoding="utf-8").replace(
                    "codex_coordinator_session_start.py", "codex_coordinator_bootstrap.sh"
                ),
                encoding="utf-8",
            ),
            "missing project lifecycle": lambda root: (
                root / "scripts" / "codex_coordinator_project.py"
            ).unlink(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = self._copy_plugin(directory)
                mutate(root)
                code, report = self._run(root, "--check")
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "broken")

    def test_extra_session_start_command_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_plugin(directory)
            path = root / "hooks" / "hooks.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            command = dict(value["hooks"]["SessionStart"][0]["hooks"][0])
            value["hooks"]["SessionStart"][0]["hooks"].append(command)
            path.write_text(json.dumps(value), encoding="utf-8")
            code, report = self._run(root, "--check")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "broken")
        self.assertIn("exactly one command", " ".join(report["findings"]))

    def test_stop_hook_contract_drift_is_rejected(self) -> None:
        def missing(root: Path) -> None:
            path = root / "hooks" / "hooks.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            del value["hooks"]["Stop"]
            path.write_text(json.dumps(value), encoding="utf-8")

        def matched(root: Path) -> None:
            path = root / "hooks" / "hooks.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["hooks"]["Stop"][0]["matcher"] = "*"
            path.write_text(json.dumps(value), encoding="utf-8")

        def slow(root: Path) -> None:
            path = root / "hooks" / "hooks.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["hooks"]["Stop"][0]["hooks"][0]["timeout"] = 6
            path.write_text(json.dumps(value), encoding="utf-8")

        def wrong_command(root: Path) -> None:
            path = root / "hooks" / "hooks.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["hooks"]["Stop"][0]["hooks"][0]["command"] = "python3 other.py"
            path.write_text(json.dumps(value), encoding="utf-8")

        for name, mutate in {
            "missing": missing,
            "matched": matched,
            "slow": slow,
            "wrong command": wrong_command,
        }.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = self._copy_plugin(directory)
                mutate(root)
                code, report = self._run(root, "--check")
                self.assertEqual(code, 1)
                self.assertEqual(report["status"], "broken")
                self.assertEqual(report["recommendedAction"], "update_or_reinstall")

    def test_compact_report_omits_paths_and_detailed_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_plugin(directory)
            (root / "skills" / "codex-coordinator" / "capabilities.json").unlink()
            code, report = self._run(root, "--compact", "--check")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "broken")
        self.assertNotIn("findings", report)
        self.assertNotIn(str(root), json.dumps(report))

    def test_legacy_apply_is_rejected_without_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_plugin(directory)
            before = _digest_tree(root)
            code, report = self._run(root, "--apply")
            after = _digest_tree(root)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "broken")
        self.assertEqual(report["recommendedAction"], "update_or_reinstall")
        self.assertEqual(before, after)

    def test_separate_repair_targets_are_rejected_without_touching_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_plugin(directory)
            external = Path(directory) / "external-skill"
            external.mkdir()
            sentinel = external / "sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            code, report = self._run(
                root,
                "--check",
                "--skill-root",
                str(external),
                "--hook-path",
                str(Path(directory) / "hook.py"),
            )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "broken")

    def test_doctor_source_has_no_repair_scanner_or_process_path(self) -> None:
        source = DOCTOR.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "os.replace",
            "copytree",
            "rollback",
            "mermaid",
            "mission_control",
            "sqlite",
            "rollout",
            "project.yaml",
        ):
            self.assertNotIn(forbidden, source.casefold())


if __name__ == "__main__":
    unittest.main()
