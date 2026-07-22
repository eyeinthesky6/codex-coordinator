from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "plugins" / "codex-coordinator" / "scripts" / "codex_coordinator_uninstall.py"
SPEC = importlib.util.spec_from_file_location("codex_coordinator_uninstall", SCRIPT)
assert SPEC and SPEC.loader
lifecycle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lifecycle
SPEC.loader.exec_module(lifecycle)


class UninstallTests(unittest.TestCase):
    def _repository(self, directory: str, *, schema: int = 2, enabled: bool = True) -> Path:
        root = Path(directory) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "--quiet", str(root)], check=True)
        coordination = root / ".codex" / "coordination"
        coordination.mkdir(parents=True)
        canonical_paths = (
            [
                "  current: .codex/coordination/CURRENT.md",
                "  tasks: .codex/coordination/tasks",
                "  suggestions: .codex/coordination/suggestions",
            ]
            if schema == 1
            else [
                "  active: .codex/coordination/active",
                "  archive: .codex/coordination/archive",
            ]
        )
        (coordination / "project.yaml").write_text(
            "\n".join(
                [
                    f"schema_version: {schema}",
                    f"coordination_enabled: {'true' if enabled else 'false'}",
                    "project_id: sample",
                    "project_name: Sample",
                    "task_prefix: SAMPLE",
                    "canonical_paths:",
                    *canonical_paths,
                    "access:",
                    "  cross_project_task_access: false",
                    "  cross_project_state_changes: false",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        if schema == 2:
            (coordination / "active").mkdir()
            (coordination / "archive").mkdir()
            (coordination / "archive" / "receipt.json").write_text("{}\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(
            "# Existing guidance\n\n" + lifecycle.DISCOVERY_BLOCK + "\n",
            encoding="utf-8",
        )
        (root / ".gitignore").write_text(lifecycle.IGNORE_BLOCK + "\n", encoding="utf-8")
        return root

    def _run(self, *args: str) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(completed.stderr, "")
        return completed.returncode, json.loads(completed.stdout)

    def test_schema_two_deactivate_is_dry_run_first_and_has_no_native_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            marker = root / ".codex" / "coordination" / "project.yaml"
            before = marker.read_bytes()
            code, plan = self._run("project", "deactivate", "--project-root", str(root))
            self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(code, 0)
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(plan["requiredNativeActions"], [])

    def test_schema_two_deactivate_and_reactivate_preserve_cold_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            receipt = root / ".codex" / "coordination" / "archive" / "receipt.json"
            code, result = self._run(
                "project", "deactivate", "--project-root", str(root), "--apply"
            )
            self.assertEqual(code, 0)
            self.assertEqual(result["requiredNativeActions"], [])
            self.assertIn(
                "coordination_enabled: false",
                (root / ".codex" / "coordination" / "project.yaml").read_text(encoding="utf-8"),
            )
            self.assertNotIn("## Codex Coordinator", (root / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertTrue(receipt.is_file())

            code, restored = self._run(
                "project", "reactivate", "--project-root", str(root), "--apply"
            )
            self.assertEqual(code, 0)
            self.assertEqual(restored["requiredNativeActions"], [])
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(agents.count(lifecycle.DISCOVERY_BLOCK), 1)
            self.assertIn("coordination_enabled: true", (root / ".codex" / "coordination" / "project.yaml").read_text(encoding="utf-8"))
            self.assertTrue(receipt.is_file())

    def test_legacy_schema_can_be_disabled_but_not_reactivated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, schema=1)
            current = root / ".codex" / "coordination" / "CURRENT.md"
            current.write_text(
                "**Coordinator thread ID:** 11111111-1111-4111-8111-111111111111\n",
                encoding="utf-8",
            )
            code, result = self._run(
                "project", "deactivate", "--project-root", str(root), "--apply"
            )
            self.assertEqual(code, 0)
            actions = [item["action"] for item in result["requiredNativeActions"]]
            self.assertIn("remove-repository-heartbeat", actions)
            self.assertIn("archive-coordinator-at-safe-boundary", actions)

            code, rejected = self._run(
                "project", "reactivate", "--project-root", str(root), "--apply"
            )
        self.assertEqual(code, 2)
        self.assertIn("migrate", rejected["error"])

    def test_schema_two_reactivation_rejects_incompatible_board_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, enabled=False)
            marker = root / ".codex" / "coordination" / "project.yaml"
            marker.write_text(
                marker.read_text(encoding="utf-8").replace(
                    ".codex/coordination/active", "../outside"
                ),
                encoding="utf-8",
            )
            code, result = self._run(
                "project", "reactivate", "--project-root", str(root), "--apply"
            )
        self.assertEqual(code, 2)
        self.assertIn("incompatible active", result["error"])

    def test_schema_one_migration_dry_run_inventories_without_importing_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, schema=1)
            coordination = root / ".codex" / "coordination"
            tasks = coordination / "tasks"
            tasks.mkdir()
            (tasks / "done.md").write_text(
                "# Preserved task\n\n**Task status:** COMPLETE\n", encoding="utf-8"
            )
            (tasks / "unknown.md").write_text("# Preserved task\n", encoding="utf-8")
            before = (coordination / "project.yaml").read_bytes()
            code, plan = self._run(
                "project", "migrate", "--project-root", str(root)
            )
            self.assertEqual((coordination / "project.yaml").read_bytes(), before)
            self.assertFalse((coordination / lifecycle.MIGRATION_BACKUP_NAME).exists())
            self.assertFalse((coordination / "active").exists())
            self.assertFalse((coordination / "archive").exists())

        self.assertEqual(code, 0)
        self.assertEqual(plan["status"], "planned")
        self.assertFalse(plan["readyToApply"])
        self.assertEqual(plan["activeClaimsCreated"], 0)
        self.assertEqual(plan["legacyState"]["taskRecords"], 2)
        self.assertEqual(plan["legacyState"]["explicitTerminalTaskRecords"], 1)
        self.assertEqual(plan["legacyState"]["unclassifiedTaskRecords"], 1)
        self.assertFalse(plan["legacyState"]["ownershipImported"])
        self.assertEqual(plan["optionalObserverState"]["status"], "not-inspected")

    def test_schema_one_migration_requires_deactivation_and_exact_confirmations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, schema=1)
            marker = root / ".codex" / "coordination" / "project.yaml"
            before = marker.read_bytes()
            code, rejected = self._run(
                "project", "migrate", "--project-root", str(root), "--apply"
            )
            self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(code, 2)
        self.assertIn("deactivate", rejected["error"])
        self.assertIn("confirm the exact project ID", rejected["error"])
        self.assertIn("legacy Coordinator heartbeat", rejected["error"])

    def test_schema_one_migration_reports_board_collision_before_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, schema=1, enabled=False)
            coordination = root / ".codex" / "coordination"
            (root / "AGENTS.md").write_text("# Existing guidance\n", encoding="utf-8")
            active = coordination / "active"
            active.mkdir()
            (active / "unexpected.json").write_text("{}\n", encoding="utf-8")
            marker_before = (coordination / "project.yaml").read_bytes()
            code, plan = self._run(
                "project",
                "migrate",
                "--project-root",
                str(root),
                "--confirm-project-id",
                "sample",
                "--confirm-legacy-runtime-stopped",
            )
            self.assertEqual((coordination / "project.yaml").read_bytes(), marker_before)
            self.assertFalse((coordination / lifecycle.MIGRATION_BACKUP_NAME).exists())
        self.assertEqual(code, 0)
        self.assertFalse(plan["readyToApply"])
        self.assertIn("board path must be absent or empty", " ".join(plan["blockers"]))

    def test_schema_one_migration_preserves_history_and_stays_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory, schema=1)
            coordination = root / ".codex" / "coordination"
            current = coordination / "CURRENT.md"
            current.write_text(
                "**Coordinator thread ID:** 11111111-1111-4111-8111-111111111111\n",
                encoding="utf-8",
            )
            tasks = coordination / "tasks"
            tasks.mkdir()
            task = tasks / "done.md"
            task.write_text("# History\n\n**Task status:** COMPLETE\n", encoding="utf-8")
            history_before = task.read_bytes()

            code, deactivated = self._run(
                "project", "deactivate", "--project-root", str(root), "--apply"
            )
            self.assertEqual(code, 0)
            self.assertEqual(deactivated["status"], "applied")
            disabled_marker = (coordination / "project.yaml").read_bytes()

            code, migrated = self._run(
                "project",
                "migrate",
                "--project-root",
                str(root),
                "--confirm-project-id",
                "sample",
                "--confirm-legacy-runtime-stopped",
                "--apply",
            )

            self.assertEqual(code, 0)
            self.assertEqual(migrated["status"], "applied")
            self.assertTrue(migrated["readyToApply"])
            marker = (coordination / "project.yaml").read_text(encoding="utf-8")
            self.assertIn("schema_version: 2", marker)
            self.assertIn("coordination_enabled: false", marker)
            self.assertIn("active: .codex/coordination/active", marker)
            self.assertIn("archive: .codex/coordination/archive", marker)
            self.assertEqual(
                (coordination / lifecycle.MIGRATION_BACKUP_NAME).read_bytes(),
                disabled_marker,
            )
            self.assertEqual(task.read_bytes(), history_before)
            self.assertEqual(list((coordination / "active").iterdir()), [])
            self.assertEqual(list((coordination / "archive").iterdir()), [])
            self.assertEqual(migrated["activeClaimsCreated"], 0)
            self.assertTrue(migrated["historyPreserved"])

    def test_purge_requires_exact_project_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            coordination = root / ".codex" / "coordination"
            code, rejected = self._run(
                "project", "purge", "--project-root", str(root), "--apply"
            )
            self.assertEqual(code, 2)
            self.assertTrue(coordination.is_dir())
            self.assertIn("confirm-project-id", rejected["error"])

            code, applied = self._run(
                "project",
                "purge",
                "--project-root",
                str(root),
                "--confirm-project-id",
                "sample",
                "--apply",
            )
            self.assertEqual(code, 0)
            self.assertFalse(coordination.exists())
            self.assertFalse((root / ".codex" / "coordination.codex-coordinator-purge").exists())
            self.assertFalse((root / "AGENTS.md").read_text(encoding="utf-8").find("## Codex Coordinator") >= 0)
            self.assertNotIn(lifecycle.IGNORE_BLOCK, (root / ".gitignore").read_text(encoding="utf-8"))
            self.assertFalse(applied["historyPreserved"])

    def test_global_plan_uses_only_verified_roots_and_reports_no_schema_two_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(directory)
            codex_home = Path(directory) / "codex-home"
            code, indexed = self._run(
                "index-project",
                "--project-root",
                str(root),
                "--codex-home",
                str(codex_home),
                "--apply",
            )
            self.assertEqual(code, 0)
            self.assertEqual(indexed["project"]["projectId"], "sample")
            code, plan = self._run("global-plan", "--codex-home", str(codex_home))
        self.assertEqual(code, 0)
        self.assertEqual(len(plan["verifiedProjects"]), 1)
        self.assertEqual(plan["verifiedProjects"][0]["requiredNativeActions"], [])
        self.assertIn("legacy schema-1", " ".join(plan["requiredGlobalActions"]))

    def test_source_never_creates_coordinator_heartbeat_or_mission_control(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"create-or-recover-coordinator"', source)
        self.assertNotIn('"pin-coordinator"', source)
        self.assertNotIn('"create-repository-heartbeat"', source)
        self.assertNotIn("start Mission Control", source)


if __name__ == "__main__":
    unittest.main()
