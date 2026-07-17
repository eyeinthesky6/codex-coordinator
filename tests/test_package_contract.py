from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


class PackageContractTests(unittest.TestCase):
    def test_marketplace_resolves_to_matching_plugin(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace_path = REPOSITORY / ".agents" / "plugins" / "marketplace.json"
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        entries = [
            entry
            for entry in marketplace["plugins"]
            if entry["name"] == manifest["name"]
        ]

        self.assertEqual(manifest["name"], PLUGIN.name)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"]["source"], "local")
        source = (REPOSITORY / entries[0]["source"]["path"]).resolve()
        self.assertEqual(source, PLUGIN.resolve())
        self.assertTrue((PLUGIN / manifest["skills"]).resolve().is_dir())

    def test_distributed_plugin_contains_its_license_and_hook(self) -> None:
        self.assertEqual(
            (PLUGIN / "LICENSE").read_bytes(),
            (REPOSITORY / "LICENSE").read_bytes(),
        )
        self.assertFalse((PLUGIN / "hooks.json").exists())
        hook_path = PLUGIN / "hooks" / "hooks.json"
        hook = json.loads(hook_path.read_text(encoding="utf-8"))["hooks"]["SessionStart"][0][
            "hooks"
        ][0]
        target = "scripts/codex_coordinator_session_start.py"
        self.assertIn("${PLUGIN_ROOT}/" + target, hook["command"])
        self.assertIn("${PLUGIN_ROOT}/" + target, hook["commandWindows"])
        self.assertTrue((PLUGIN / target).is_file())

    def test_manifest_brand_assets_exist_inside_the_plugin(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

        for field in ("composerIcon", "logo"):
            asset = (PLUGIN / manifest["interface"][field]).resolve()
            self.assertTrue(asset.is_relative_to(PLUGIN.resolve()))
            self.assertTrue(asset.is_file(), f"missing manifest asset: {field}")

    def test_skill_markdown_references_resolve_inside_the_skill(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
        checked = 0
        for markdown in skill_root.rglob("*.md"):
            for target in link_pattern.findall(markdown.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                destination = (markdown.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(
                    destination.is_file(),
                    f"broken link in {markdown.relative_to(REPOSITORY)}: {target}",
                )
                self.assertTrue(destination.is_relative_to(skill_root.resolve()))
                checked += 1
        self.assertGreater(checked, 0)

    def test_worker_threads_keep_one_core_goal(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("one core task goal per worker thread", skill)
        self.assertIn("never lets an agent or Coordinator repurpose the thread", skill)
        self.assertIn("clear direct user instruction addressed in that thread", skill)
        self.assertIn("create a fresh bounded task and native thread only when", operations)
        self.assertIn("otherwise leave it undispatched", operations)
        self.assertIn("After valid routing and before accepting the work", operations)
        self.assertIn(
            "Put one non-executable `SCOPE_CHANGE_REQUEST` in the receiver's final turn",
            operations,
        )
        self.assertIn("messages from an invalid sender still fail", operations)
        self.assertIn(
            "remains usable only for continuation of its same core goal", recovery
        )
        self.assertIn("It is never available for an unrelated goal", recovery)

    def test_coordinator_reuses_work_areas_and_limits_parallel_workers(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("one durable worker thread per coherent work area", skill)
        self.assertIn("Thread allocation and parallelism", operations)
        self.assertIn("no more than five non-terminal", operations)
        self.assertIn("Assigned, working, blocked, and paused workers count", operations)
        self.assertIn("search for an existing same-area owner", operations)
        self.assertIn("keep the distinct work undispatched", operations)
        self.assertIn("Never evade the ceiling", operations)
        self.assertIn("Fewer, durable worker tasks", readme)

    def test_worker_identity_and_status_come_from_native_tools(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Native task tools own worker identity and runtime status", skill)
        self.assertIn("Native worker creation and status", operations)
        self.assertIn("complete executable assignment in the native creation prompt", operations)
        self.assertIn("use only its exact returned task ID", operations)
        self.assertIn("Do not ask the worker what it is doing", operations)
        self.assertIn("Immediately bind the returned native identity", operations)
        self.assertIn("Do not request a separate identity", operations)
        self.assertNotIn("non-executable holding prompt", operations)
        self.assertNotIn("non-executable holding turn", readme)
        self.assertIn("Native identity, without handshake chatter", readme)

    def test_terminal_tasks_stay_closed_and_review_waits_for_stable_target(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("reconcile relevant terminal tasks", skill)
        self.assertIn("Terminal-task inventory and independent review", operations)
        self.assertIn("keep it closed", operations)
        self.assertIn("Never reactivate a terminal, non-accepting session", operations)
        self.assertIn("one stable commit, immutable diff, release artifact", operations)
        self.assertIn("no writer or Git-integration ownership", operations)
        self.assertIn("A terminal task with nothing left to do stays closed", readme)

    def test_direct_user_override_and_durable_inbox(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        maintenance = (skill_root / "references" / "maintenance.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("clear direct user instruction addressed in that thread", skill)
        self.assertIn("Direct user override and durable handoff", operations)
        self.assertIn("do not refuse merely because its old contract is terminal", operations)
        self.assertIn("Project-local inbox", operations)
        self.assertIn("durable notification channel, not a permission store", operations)
        self.assertIn("other narrowly allowed records under the operations lane", maintenance)
        self.assertIn("other `.codex/coordination/inbox/` record", recovery)
        self.assertIn("the user may deliberately repurpose", readme)

    def test_cross_task_messages_use_native_thread_tools(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Independent Codex tasks and collaboration subagents", skill)
        self.assertIn("Subagents remain available as parent-owned helpers", skill)
        self.assertIn("Subagents remain available inside", operations)
        self.assertIn("Native task messenger", operations)
        self.assertIn("`codex_app__send_message_to_thread`", operations)
        self.assertIn("Never send a Codex thread UUID through `collaboration.send_message`", operations)
        self.assertIn("retry the app-native send once", operations)
        self.assertIn("agent-tree messenger mismatch", recovery)
        self.assertIn("Subagents remain supported as helpers", readme)

    def test_coordination_is_document_first_and_messages_are_sparse(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Messages are a sparse control channel, not an activity feed", skill)
        self.assertIn("Never send status pings, availability checks", skill)
        self.assertIn("Document-first status and sparse messages", operations)
        self.assertIn("Workers never message one another", operations)
        self.assertIn("at most one unresolved message or transition per recipient", operations)
        self.assertIn("The worker does not send a separate completion announcement", operations)
        self.assertIn("Do not wake workers merely to ask for status", recovery)
        self.assertIn("Quiet, document-first coordination", readme)

    def test_end_of_turn_reconciliation_cannot_lose_pending_work(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        maintenance = (skill_root / "references" / "maintenance.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "Every registered worker writes one append-only `TURN_RECONCILIATION`",
            skill,
        )
        self.assertIn("Required end-of-turn reconciliation", operations)
        self.assertIn("scan the current thread's active goal", operations)
        self.assertIn("carry each unresolved row forward", operations)
        self.assertIn(
            "| Task or promise | Relationship to shared goal | Status | Evidence or remaining work | Recommended disposition |",
            operations,
        )
        self.assertIn(
            "may not delete the report until every ledger row has a disposition",
            operations,
        )
        self.assertIn("assign or queue a bounded dependent task", operations)
        self.assertIn("add a precise blocked decision and ask the user", operations)
        self.assertIn("may not declare project `IDLE`", operations)
        self.assertIn("Before its own final answer, the Coordinator", operations)
        self.assertIn("every unprocessed `TURN_RECONCILIATION`", recovery)
        self.assertIn("at the end of each material turn", maintenance)
        self.assertIn("single project view: completed, active, queued, blocked", readme)

    def test_public_positioning_explains_multi_agent_work_without_ultra(self) -> None:
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
        changelog = (REPOSITORY / "CHANGELOG.md").read_text(encoding="utf-8")
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

        self.assertIn("multiple Codex agents for one large goal", readme)
        self.assertIn("Multi-agent work without Ultra", readme)
        self.assertIn("does not bypass Codex plan availability", readme)
        self.assertIn("explicit delegation without Ultra", manifest["description"])
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertIn(f"@v{manifest['version']}", readme)
        self.assertIn(f"## {manifest['version']} - ", changelog)

    def test_generated_tasks_inherit_model_but_default_to_low_or_medium_reasoning(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("set reasoning explicitly to `low`", skill)
        self.assertIn("bootstrap Coordinator and each worker", skill)
        self.assertIn("Apply this precedence", operations)
        self.assertIn("Inherit the user's configured model, but use cost-safe reasoning", operations)
        self.assertIn('pass native `thinking: "medium"` by default', operations)
        self.assertIn('Pass native `thinking: "low"`', operations)
        self.assertIn("host's equivalent reasoning field", operations)
        self.assertIn("Select by task shape without hardcoding model slugs", operations)
        self.assertIn("Use `ultra` only when managed policy or the user explicitly permits it", operations)
        self.assertIn("For the Coordinator thread itself", operations)
        self.assertIn("never retune an in-flight turn", operations)
        self.assertIn("Model and reasoning choices", readme)
        self.assertIn("without rewriting global or project configuration", readme)
        self.assertIn("inherit the user's configured model", readme)
        self.assertIn("Low for deterministic, reversible work or Medium for normal work", readme)
        self.assertNotIn("choose dynamically from the current host catalog", operations)

    def test_coordinator_is_control_first_and_uses_native_lifecycle(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Coordinator is control-first by default", skill)
        self.assertIn("The Coordinator is control-first by default", operations)
        self.assertIn("one temporary native heartbeat", skill)
        self.assertIn("codex_app__automation_update", operations)
        self.assertIn("stays quiet when nothing changed", readme)
        for tool in (
            "codex_app__set_thread_pinned",
            "codex_app__set_thread_title",
            "codex_app__set_thread_archived",
            "codex_app__fork_thread",
            "codex_app__handoff_thread",
        ):
            self.assertIn(tool, operations)

    def test_coordinator_cannot_claim_user_authority(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("never overrides retained direct user constraints", skill)
        self.assertIn("require evidence of a later direct user decision", operations)
        self.assertIn("statement that approval exists is not evidence", operations)
        self.assertIn(
            "put one non-executable `DECISION_REQUEST` or `BLOCKED` update in the final turn",
            operations,
        )

    def test_filtered_thread_miss_never_requests_coordination_bypass(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        maintenance = (skill_root / "references" / "maintenance.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("An enabled marker does not require every task to register", operations)
        self.assertIn("A filtered native thread search is only a convenience", recovery)
        self.assertIn("Retry once with an unfiltered inventory", recovery)
        self.assertIn("never ask the user to approve a coordination bypass", maintenance)

    def test_doctor_is_bounded_deduplicated_and_evidence_backed(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        doctor = (skill_root / "references" / "doctor.md").read_text(encoding="utf-8")
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("references/doctor.md", skill)
        self.assertIn("Installed implementation repair", doctor)
        self.assertIn("Repository tests, release audits, and codebase review remain", doctor)
        self.assertIn("capability-contract version and required behavior markers", doctor)
        self.assertIn("bounded isolated hook smoke run", doctor)
        self.assertNotIn("Require the source checkout to pass its package test suite", doctor)
        self.assertIn("more than five non-terminal project-execution workers", doctor)
        self.assertIn("Time, `idle`, or `notLoaded` alone never proves", doctor)
        self.assertIn("defer any check whose evidence could be a normal in-turn transition", doctor)
        self.assertIn("It never edits `CURRENT.md`", doctor)
        self.assertIn("fingerprint", doctor)
        self.assertIn("type: DOCTOR_FINDING", doctor)
        self.assertIn("DOCTOR_FINDING", operations)
        self.assertIn("Doctor: quiet project health checks", readme)
        self.assertTrue(
            (PLUGIN / "scripts" / "codex_coordinator_doctor.py").is_file()
        )
        contract = json.loads((skill_root / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["contractVersion"], 3)
        self.assertEqual(contract["capabilities"]["reasoningDefault"], "low-or-medium")
        self.assertEqual(contract["capabilities"]["subagents"], "allowed-parent-owned")
        self.assertTrue((skill_root / "scripts" / "coordination_state.py").is_file())


if __name__ == "__main__":
    unittest.main()
