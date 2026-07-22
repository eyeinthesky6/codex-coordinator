from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
SKILL = PLUGIN / "skills" / "codex-coordinator"


class PackageContractTests(unittest.TestCase):
    def test_manifest_and_marketplace_are_public_and_consistent(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((REPOSITORY / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "codex-coordinator")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn("boundar", manifest["description"].casefold())
        self.assertIn("without a resident coordinator", manifest["interface"]["longDescription"].casefold())
        self.assertEqual(marketplace["plugins"][0]["name"], manifest["name"])
        self.assertEqual(marketplace["plugins"][0]["source"]["path"], "./plugins/codex-coordinator")

    def test_prompts_offer_visibility_and_claims_not_task_fanout(self) -> None:
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        prompts = " ".join(manifest["interface"]["defaultPrompt"]).casefold()
        agent = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8").casefold()
        self.assertIn("active task boundaries", prompts)
        self.assertIn("bounded paths", prompts)
        self.assertNotIn("create the tasks needed", prompts + agent)
        self.assertNotIn("run doctor across", prompts + agent)

    def test_contract_is_small_and_matches_accepted_architecture(self) -> None:
        contract = json.loads((SKILL / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contractVersion"], 22)
        capabilities = contract["capabilities"]
        self.assertEqual(len(capabilities), 19)
        expected = {
            "corePurpose": "repository-task-boundary-visibility",
            "repositoryLifecycle": "explicit-opt-in",
            "projectLifecycleTool": "dry-run-first-init-deactivate-migrate-reactivate-purge",
            "defaultExecution": "one-native-task",
            "nativeTaskAuthority": "execution-messaging-transcript",
            "claimOwnership": "per-task-json-record",
            "messagePolicy": "sparse-non-executable-peer-notices",
            "transcriptStorage": "none",
            "sessionStart": "marker-only-no-child-process",
            "doctor": "read-only-compatibility-reinstall",
            "missionControl": "not-shipped-separate-package-only",
            "gitWorkflow": "direct-commit-default-pr-optional",
        }
        for key, value in expected.items():
            self.assertEqual(capabilities[key], value)

    def test_skill_links_are_internal_and_resolve(self) -> None:
        source = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(source.startswith("---\nname: codex-coordinator\n"))
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", source):
            self.assertNotIn("://", link)
            self.assertTrue((SKILL / link).is_file(), link)

    def test_guidance_is_modular_but_not_a_reconciliation_hot_path(self) -> None:
        operations = (SKILL / "references" / "operations.md").read_text(encoding="utf-8")
        reconciliation = (SKILL / "references" / "reconciliation.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(operations.splitlines()), 15)
        self.assertIn("not a reconciliation loop", operations)
        self.assertIn("Retired reconciliation lane", reconciliation)
        self.assertLessEqual(len(reconciliation.splitlines()), 10)

    def test_execution_retains_limits_overlap_and_direct_git_workflow(self) -> None:
        execution = (SKILL / "references" / "execution.md").read_text(encoding="utf-8")
        for phrase in (
            "One task is the default",
            "Three active durable tasks is the default maximum",
            "twelve is the hard limit",
            "ancestor",
            "git-integration",
            "Direct commits and pushes",
            "Pull requests are optional",
        ):
            self.assertIn(phrase, execution)

    def test_messages_are_sparse_non_executable_and_have_no_ack_chain(self) -> None:
        messaging = (SKILL / "references" / "messaging.md").read_text(encoding="utf-8")
        for message_type in ("COLLISION", "DEPENDENCY", "RELEASED"):
            self.assertIn(message_type, messaging)
        self.assertIn("non-executable", messaging)
        self.assertIn("or acknowledgement messages", messaging)
        self.assertNotIn("STATUS", messaging)

    def test_recovery_never_uses_silence_or_idle_as_stale_evidence(self) -> None:
        recovery = (SKILL / "references" / "recovery.md").read_text(encoding="utf-8")
        self.assertIn("Exact evidence first", recovery)
        self.assertIn("Time, silence", recovery)
        self.assertIn("stale-owner-confirmed", recovery)
        self.assertIn("Preserve `CURRENT.md`", recovery)

    def test_installation_is_opt_in_and_creates_no_runtime_components(self) -> None:
        installation = (SKILL / "references" / "installation.md").read_text(encoding="utf-8")
        self.assertIn("schema_version: 2", installation)
        self.assertIn("coordination_enabled: false", installation)
        self.assertIn("Mission Control is not started", installation)
        self.assertIn("Do not create a Codex task", installation)
        self.assertIn("never store transcripts", installation)

    def test_doctor_and_maintenance_assign_repair_to_plugin_manager(self) -> None:
        doctor = (SKILL / "references" / "doctor.md").read_text(encoding="utf-8")
        maintenance = (SKILL / "references" / "maintenance.md").read_text(encoding="utf-8")
        self.assertIn("manual, read-only compatibility check", doctor)
        self.assertIn("Update or reinstall", doctor)
        self.assertIn("Legacy `--apply` requests are rejected", doctor)
        self.assertIn("normal plugin manager", maintenance)
        self.assertIn("no Coordinator task, pin, heartbeat", maintenance)

    def test_session_start_is_direct_and_optional_tools_are_not_required(self) -> None:
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        hook = hooks["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertEqual(hook["timeout"], 5)
        self.assertIn("codex_coordinator_session_start.py", hook["command"])
        self.assertNotIn("mission", json.dumps(hook).casefold())
        self.assertFalse((PLUGIN / "scripts" / "codex_coordinator_bootstrap.ps1").exists())
        self.assertFalse((PLUGIN / "scripts" / "codex_coordinator_bootstrap.sh").exists())

    def test_package_contains_no_mission_control_runtime(self) -> None:
        runtime = PLUGIN / "mission_control"
        shipped_files = [
            path
            for path in runtime.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        self.assertEqual(shipped_files, [])
        self.assertFalse((PLUGIN / "scripts" / "mission_control_lifecycle.py").exists())
        source_wrapper = REPOSITORY / "apps" / "mission_control"
        wrapper_files = [
            path
            for path in source_wrapper.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]
        self.assertEqual(wrapper_files, [])
        self.assertFalse((REPOSITORY / "tests" / "verify_mission_control_ui.py").exists())

    def test_core_runtime_has_no_private_codex_or_transcript_coupling(self) -> None:
        core = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                PLUGIN / "scripts" / "codex_coordinator_session_start.py",
                PLUGIN / "scripts" / "codex_coordinator_doctor.py",
                SKILL / "scripts" / "coordination_state.py",
            )
        ).casefold()
        for forbidden in ("state_*.sqlite", "rollout_tail", "read_thread", "wait_threads", "current.md"):
            self.assertNotIn(forbidden, core)
        self.assertNotIn("subprocess", core)

    def test_project_marker_remains_disabled_during_realign(self) -> None:
        marker = (REPOSITORY / ".codex" / "coordination" / "project.yaml").read_text(encoding="utf-8")
        self.assertIn("schema_version: 2", marker)
        self.assertIn("coordination_enabled: false", marker)
        self.assertIn("active: .codex/coordination/active", marker)
        self.assertIn("archive: .codex/coordination/archive", marker)

    def test_package_contains_no_live_project_state_or_private_paths(self) -> None:
        packaged = [path for path in PLUGIN.rglob("*") if path.is_file()]
        relative = [path.relative_to(PLUGIN).as_posix() for path in packaged]
        self.assertFalse(any(".codex/coordination/active" in item for item in relative))
        self.assertFalse(any(".codex/coordination/archive" in item for item in relative))
        for path in packaged:
            if path.suffix.lower() not in {".py", ".md", ".json", ".yaml", ".yml", ".ps1", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn("C:\\Users\\Six Ideas", text)

    def test_decision_record_contains_history_retained_protections_and_rollback(self) -> None:
        review = (REPOSITORY / "docs" / "codebase" / "2026-07-21_boundary-board-simplification_architectural_review.md").read_text(encoding="utf-8")
        for heading in (
            "Symptoms that triggered the review",
            "Original guidance files versus current guidance",
            "Capability-contract evolution",
            "Protections that must remain",
            "Deeper failure-mode review",
            "Doctor decision",
            "Mission Control decision",
            "Rollback",
            "Performance acceptance",
        ):
            self.assertIn(heading, review)


if __name__ == "__main__":
    unittest.main()
