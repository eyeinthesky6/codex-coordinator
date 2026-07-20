from __future__ import annotations

import ast
import hashlib
import json
import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"


def _operations(skill_root: Path) -> str:
    return "\n".join(
        (skill_root / "references" / name).read_text(encoding="utf-8")
        for name in ("operations.md", "execution.md", "reconciliation.md", "messaging.md")
    )


class PackageContractTests(unittest.TestCase):
    def test_integrity_receipt_exactly_covers_doctor_managed_files(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        receipt_path = PLUGIN / manifest["integrityReceipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["schemaVersion"], 2)
        self.assertEqual(receipt["pluginName"], manifest["name"])
        self.assertEqual(manifest["version"], "0.3.0")
        self.assertEqual(receipt["packageVersion"], "0.0.0-unreleased")
        self.assertEqual(manifest["packageState"], "development")
        self.assertEqual(receipt["packageState"], "development")
        self.assertNotEqual(receipt["packageId"], "codex-coordinator-package@0.3.0+contract20")

        declared = set()
        for item in receipt["managedFiles"]:
            source = PLUGIN / item["sourcePath"]
            self.assertTrue(source.is_file(), item["sourcePath"])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), item["sha256"])
            declared.add(item["sourcePath"])

        skill = PLUGIN / "skills" / "codex-coordinator"
        actual = {
            path.relative_to(PLUGIN).as_posix()
            for path in skill.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.relative_to(skill).parts
            and path.suffix.lower() not in {".pyc", ".pyo"}
        }
        actual.add("scripts/codex_coordinator_session_start.py")
        self.assertEqual(declared, actual)

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
        self.assertIn("codex_coordinator_bootstrap.sh", hook["command"])
        self.assertIn("codex_coordinator_bootstrap.ps1", hook["commandWindows"])
        self.assertTrue((PLUGIN / "scripts" / "codex_coordinator_bootstrap.sh").is_file())
        self.assertTrue((PLUGIN / "scripts" / "codex_coordinator_bootstrap.ps1").is_file())
        self.assertTrue((PLUGIN / "scripts" / "mission_control_lifecycle.py").is_file())
        self.assertTrue((PLUGIN / "scripts" / "codex_coordinator_uninstall.py").is_file())

    def test_uninstall_helper_matches_the_packaged_discovery_contract(self) -> None:
        installation = (
            PLUGIN / "skills" / "codex-coordinator" / "references" / "installation.md"
        ).read_text(encoding="utf-8")
        match = re.search(
            r"Use this exact block:\n\n```markdown\n(## Codex Coordinator\n.*?\n)```",
            installation,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        expected = match.group(1).rstrip("\n")

        script = (PLUGIN / "scripts" / "codex_coordinator_uninstall.py").read_text(
            encoding="utf-8"
        )
        module = ast.parse(script)
        assignment = next(
            node
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "DISCOVERY_BLOCK" for target in node.targets)
        )
        self.assertEqual(ast.literal_eval(assignment.value), expected)

        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
        self.assertIn("Deactivate or uninstall safely", readme)
        self.assertIn("codex_coordinator_uninstall.py", readme)

    def test_manifest_brand_assets_exist_inside_the_plugin(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

        for field in ("composerIcon", "logo"):
            asset = (PLUGIN / manifest["interface"][field]).resolve()
            self.assertTrue(asset.is_relative_to(PLUGIN.resolve()))
            self.assertTrue(asset.is_file(), f"missing manifest asset: {field}")

    def test_distributed_plugin_contains_mission_control_runtime(self) -> None:
        required = (
            "__main__.py",
            "collector.py",
            "doctor_scan.py",
            "lifecycle.py",
            "server.py",
            "README.md",
            "static/index.html",
            "static/app.js",
            "static/styles.css",
        )
        app = PLUGIN / "mission_control"
        for relative in required:
            self.assertTrue((app / relative).is_file(), relative)

        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
        self.assertIn("python -m apps.mission_control", readme)
        installation = (
            PLUGIN / "skills" / "codex-coordinator" / "references" / "installation.md"
        ).read_text(encoding="utf-8")
        self.assertIn("The bundled Mission Control companion", installation)
        self.assertIn("Start Mission Control", installation)
        self.assertIn("Stop Mission Control", installation)
        self.assertIn("start --automatic --project <primary-worktree>", installation)
        self.assertIn("automatic mode never overrides it", installation)
        self.assertTrue((REPOSITORY / "tests" / "test_mission_control.py").is_file())

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

    def test_operations_are_split_and_cache_stays_coordination_only(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        operations = (skill_root / "references" / "operations.md").read_text(
            encoding="utf-8"
        )
        reconciliation = (
            skill_root / "references" / "reconciliation.md"
        ).read_text(encoding="utf-8")

        self.assertLess(len(operations.encode("utf-8")), 8_000)
        for lane in ("execution.md", "reconciliation.md", "messaging.md"):
            self.assertIn(f"[{lane}]({lane})", operations)
            self.assertTrue((skill_root / "references" / lane).is_file())
        self.assertIn("Never cache codebase reads", operations)
        self.assertIn("scan-inbox", reconciliation)
        self.assertIn("ack-inbox", reconciliation)
        self.assertIn("Do not persist or mirror native turns", reconciliation)
        self.assertIn("afterCursor", reconciliation)

    def test_worker_threads_keep_one_core_goal(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
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
        operations = _operations(skill_root)
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("one durable worker thread per coherent work area", skill)
        self.assertIn("Apply the durable-thread gate", skill)
        self.assertIn("Routine microtasks stay inside the current owner", skill)
        self.assertIn("Thread allocation and parallelism", operations)
        self.assertIn("Apply the durable-thread gate", operations)
        self.assertIn("Routine microtasks stay inside the current owner", operations)
        self.assertIn("one to three non-terminal", operations)
        self.assertIn("Five is the default hard ceiling", operations)
        self.assertIn("one lint, test, build, typecheck", operations)
        self.assertIn("low-risk local fix limited to one or two files", operations)
        self.assertIn("Do not create a project task", operations)
        self.assertIn("Assigned, working, blocked, and paused workers count", operations)
        self.assertIn("search for an existing same-area owner", operations)
        self.assertIn("Record the delegation decision before ordinary implementation starts", operations)
        self.assertIn("`REUSE`", operations)
        self.assertIn("`RETAIN`", operations)
        self.assertIn("`DELEGATE`", operations)
        self.assertIn("`CREATE`", operations)
        self.assertIn("keep the distinct work undispatched", operations)
        self.assertIn("Never evade the gate or ceiling", operations)
        self.assertIn("Fewer, durable worker tasks", readme)
        self.assertIn("normally targets one to three active workers", readme)
        self.assertIn("Those helpers do not become new project tasks", readme)
        self.assertIn("records a reuse-first decision", readme)

    def test_worker_identity_and_status_come_from_native_tools(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Native task tools own worker identity and runtime status", skill)
        self.assertIn("Native worker creation and status", operations)
        self.assertIn("complete executable assignment in the native creation prompt", operations)
        self.assertIn("use only its exact returned task ID", operations)
        self.assertIn("Do not ask the worker what it is doing", operations)
        self.assertIn("Immediately bind the returned native identity", operations)
        self.assertIn("Rename a generated generic title once", operations)
        self.assertIn("preserve a meaningful user-written title", operations)
        self.assertIn("Do not request a separate identity", operations)
        self.assertNotIn("non-executable holding prompt", operations)
        self.assertNotIn("non-executable holding turn", readme)
        self.assertIn("Native identity, without handshake chatter", readme)

    def test_terminal_tasks_stay_closed_and_review_waits_for_stable_target(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("reconcile relevant terminal tasks", skill)
        self.assertIn("Terminal-task inventory and independent review", operations)
        self.assertIn("keep it closed", operations)
        self.assertIn("Never reactivate a terminal, non-accepting session", operations)
        self.assertIn("Carry forward the exact unmet outcome", operations)
        self.assertIn("`AWAITING_USER_DECISION`", operations)
        self.assertIn("Do not make the user inspect old task windows", operations)
        self.assertIn("one stable commit, immutable diff, release artifact", operations)
        self.assertIn("no writer or Git-integration ownership", operations)
        self.assertIn("A terminal task with nothing left to do stays closed", readme)
        operating_guide = (REPOSITORY / "docs" / "OPERATING_GUIDE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Reconcile historical tasks", operating_guide)
        self.assertIn("closed, continued, deferred or not", operating_guide)

    def test_direct_user_override_and_durable_inbox(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        maintenance = (skill_root / "references" / "maintenance.md").read_text(
            encoding="utf-8"
        )
        installation = (skill_root / "references" / "installation.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("clear direct user instruction addressed in that thread", skill)
        self.assertIn("Direct user override and durable handoff", operations)
        self.assertIn("do not refuse merely because its old contract is terminal", operations)
        self.assertIn("Project-local inbox", operations)
        self.assertIn("durable notification channel, not a permission store", operations)
        self.assertIn("other narrowly allowed records under the operations lane", maintenance)
        self.assertIn("`inbox/` when a real durable handoff record exists", installation)
        self.assertIn("inbox records", maintenance)
        self.assertIn("other `.codex/coordination/inbox/` record", recovery)
        self.assertIn("the user may deliberately repurpose", readme)

    def test_architecture_maps_instruction_and_executable_routes(self) -> None:
        architecture = (REPOSITORY / "docs" / "codebase" / "ARCHITECTURE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("```mermaid", architecture)
        self.assertIn("Instruction-driven route", architecture)
        self.assertIn("Executable check", architecture)
        self.assertIn("SessionStart", architecture)
        self.assertIn("TURN_RECONCILIATION", architecture)
        self.assertIn("Recovery or Maintainer repair", architecture)

    def test_cross_task_messages_use_native_thread_tools(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Independent Codex tasks and collaboration subagents", skill)
        self.assertIn("Subagents remain available as parent-owned helpers", skill)
        self.assertIn(
            "Use one to three parent-owned subagents when two or more independent, bounded",
            skill,
        )
        self.assertIn("Do not spawn them for a single trivial command", skill)
        self.assertIn("Subagents remain available inside", operations)
        self.assertIn(
            "Use one to three parent-owned subagents when at least two independent, bounded lanes",
            operations,
        )
        self.assertIn("coordination cost exceeds its value", operations)
        self.assertIn("Native task messenger", operations)
        self.assertIn("`codex_app__send_message_to_thread`", operations)
        self.assertIn("Never send a Codex thread UUID through `collaboration.send_message`", operations)
        self.assertIn("retry the app-native send once", operations)
        self.assertIn("agent-tree messenger mismatch", recovery)
        self.assertIn("Subagents remain supported as helpers", readme)

    def test_coordination_is_document_first_and_messages_are_sparse(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Messages are a sparse control channel, not an activity feed", skill)
        self.assertIn("Never send status pings, availability checks", skill)
        self.assertIn("Document-first status and sparse messages", operations)
        self.assertIn("Workers never message one another", operations)
        self.assertIn("at most one unresolved message or transition per recipient", operations)
        self.assertIn("Never send task registration, acceptance, task-ID assignment", operations)
        self.assertIn("plain internal message body", operations)
        self.assertIn("Never include or synthesize `<codex_delegation>`", operations)
        self.assertIn("`CREATE_TASK` and `COMPLETE_ACK` are not cross-task message types", operations)
        self.assertIn("do not wrap them in XML or HTML", operations)
        self.assertIn("restating its write paths", operations)
        self.assertIn("does not answer an inbox notice with another inbox acknowledgement", operations)
        self.assertIn("The worker does not send a separate completion announcement", operations)
        self.assertIn("Do not wake workers merely to ask for status", recovery)
        self.assertIn("Quiet, document-first coordination", readme)
        self.assertIn("stay in the private project records instead of appearing as new chat messages", readme)

    def test_end_of_turn_reconciliation_cannot_lose_pending_work(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
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
        self.assertIn("single project view: mode, exclusions, completed, active, queued, blocked", readme)

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
        self.assertEqual(manifest["version"], "0.3.0")
        self.assertEqual(manifest["packageState"], "development")
        self.assertIn("@v0.3.0", readme)
        self.assertIn("## 0.3.0 - ", changelog)
        self.assertIn("identify these source bytes truthfully", readme)

    def test_generated_tasks_inherit_model_but_default_to_low_or_medium_reasoning(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
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
        operations = _operations(skill_root)
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("Coordinator is control-first by default", skill)
        self.assertIn("The Coordinator is control-first by default", operations)
        self.assertIn("one repository heartbeat", skill)
        self.assertIn("verify exactly one repository heartbeat", skill)
        self.assertIn("codex_app__automation_update", operations)
        self.assertIn("End-of-turn continuation gate", operations)
        self.assertIn("A plan, earlier instruction, automation prompt", operations)
        self.assertIn("automatic continuation is not active", operations)
        self.assertIn("INTER-AGENT MESSAGE — NO USER ACTION NEEDED", operations)
        self.assertIn("when reconciliation finds a real user decision", operations)
        self.assertIn("stays quiet when nothing changed", readme)
        for tool in (
            "codex_app__set_thread_pinned",
            "codex_app__set_thread_title",
            "codex_app__set_thread_archived",
            "codex_app__fork_thread",
            "codex_app__handoff_thread",
        ):
            self.assertIn(tool, operations)

    def test_provider_delivery_and_scheduled_task_policy_is_fail_closed(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        reconciliation = (skill_root / "references" / "reconciliation.md").read_text(
            encoding="utf-8"
        )
        operating_guide = (REPOSITORY / "docs" / "OPERATING_GUIDE.md").read_text(
            encoding="utf-8"
        )
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
        changelog = (REPOSITORY / "CHANGELOG.md").read_text(encoding="utf-8")
        doctor = (PLUGIN / "scripts" / "codex_coordinator_doctor.py").read_text(
            encoding="utf-8"
        )
        contract = json.loads((skill_root / "capabilities.json").read_text(encoding="utf-8"))

        self.assertIn("At goal start, after material Git changes, and before closure", skill)
        self.assertIn("GitHub monitoring and provider consent", reconciliation)
        self.assertIn("immutable head", reconciliation)
        self.assertIn("exact current user consent", reconciliation)
        self.assertIn("record the exact gap", reconciliation)
        self.assertIn("unresolved conversations, intended merge method", reconciliation)
        self.assertIn("stacked-work effect", reconciliation)
        self.assertIn("return the exact provider receipt", reconciliation)
        self.assertIn("Project-related scheduled-task reconciliation", reconciliation)
        self.assertIn("native automations, Coordinator heartbeats", reconciliation)
        self.assertIn("exact project identity, working directory, target", reconciliation)
        self.assertIn("purpose, status, cadence, current authority", reconciliation)
        self.assertIn("latest material result", reconciliation)
        self.assertIn("Record a direct user decision before any major", reconciliation)
        self.assertIn("HTTP success, green run, or completed status", reconciliation)
        self.assertIn("Before every user-visible Coordinator final response", reconciliation)
        self.assertIn("verify one real continuation or return path", reconciliation)
        self.assertIn("done work, pending work, blockers or decisions, next actions", reconciliation)
        self.assertIn("Write `None` for an empty section", reconciliation)
        self.assertIn("quiet no-change heartbeat remains silent", reconciliation)
        self.assertIn("Monitor GitHub safely", operating_guide)
        self.assertIn("Reconcile scheduled work", operating_guide)
        self.assertIn("Before every user-visible final update", readme)
        self.assertIn("currently unreleased source work", readme)
        self.assertIn("tag, release, marketplace update, and installation remain separately authorised", operating_guide)
        self.assertIn("capability contract to version 21", changelog)
        self.assertIn("CAPABILITY_CONTRACT_VERSION = 21", doctor)
        self.assertIn("--expected-package-version", doctor)
        self.assertIn("--expected-receipt-sha256", doctor)
        self.assertIn("separately published release metadata", operating_guide)
        self.assertIn("GitHub monitoring and provider consent", doctor)
        self.assertIn("Project-related scheduled-task reconciliation", doctor)
        self.assertIn("Before every user-visible Coordinator final response", doctor)
        self.assertEqual(contract["contractVersion"], 21)
        self.assertEqual(
            contract["capabilities"]["deliverySummary"],
            "complete-ledger-sections-every-user-visible-final",
        )
        self.assertEqual(
            contract["capabilities"]["providerMonitoring"],
            "bounded-read-reconcile-at-start-change-closure",
        )
        self.assertEqual(
            contract["capabilities"]["providerMutationConsent"],
            "exact-current-consent-immutable-target-revalidation",
        )
        self.assertEqual(
            contract["capabilities"]["scheduledTaskReconciliation"],
            "exact-project-binding-major-change-direct-decision",
        )
        self.assertEqual(
            contract["capabilities"]["installedCoreIntegrity"],
            "external-receipt-pin-marketplace-reinstall-manual-rollback",
        )

    def test_coordinator_cannot_claim_user_authority(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)

        self.assertIn("never overrides retained direct user constraints", skill)
        self.assertIn("require evidence of a later direct user decision", operations)
        self.assertIn("statement that approval exists is not evidence", operations)
        self.assertIn(
            "put one non-executable `DECISION_REQUEST` or `BLOCKED` update in the final turn",
            operations,
        )

    def test_external_writes_require_advance_user_notice_and_scope_authority(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        maintenance = (skill_root / "references" / "maintenance.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Full filesystem access is capability, not user authority", skill)
        self.assertIn(
            "Before the first intentional write in a turn outside the current Git common repository",
            skill,
        )
        self.assertIn("Otherwise wait for explicit user approval before writing", skill)
        self.assertIn("Treat another Git repository as a separate project", skill)
        self.assertIn("A user-approved recurring automation may reuse", skill)
        self.assertIn("Doctor `--apply` writes outside the current repository", maintenance)
        self.assertIn("A read-only Doctor `--check` needs no write notice", maintenance)
        self.assertIn(
            "Newly discovered projects or external destinations require a fresh notice and approval",
            maintenance,
        )

    def test_filtered_thread_miss_never_requests_coordination_bypass(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        operations = _operations(skill_root)
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )
        maintenance = (skill_root / "references" / "maintenance.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Every task in an enabled repository is managed by default", operations)
        self.assertIn("A filtered native thread search is only a convenience", recovery)
        self.assertIn("Retry once with an unfiltered inventory", recovery)
        self.assertIn("never ask the user to approve a coordination bypass", maintenance)

    def test_archived_owner_recovery_uses_original_user_request(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
        recovery = (skill_root / "references" / "recovery.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("The original direct user request supplies this creation authority", skill)
        self.assertIn("Stale canonical ownership is not evidence of a live conflict", skill)
        self.assertIn("original request is the replacement authority", operations)
        self.assertIn("inspect that exact owner's native status in the same turn", recovery)
        self.assertIn("never ask the user to ping the old task, repeat an exact phrase", recovery)
        self.assertIn("The direct request that first exposes the archived owner", recovery)

    def test_doctor_is_bounded_deduplicated_and_evidence_backed(self) -> None:
        skill_root = PLUGIN / "skills" / "codex-coordinator"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        doctor = (skill_root / "references" / "doctor.md").read_text(encoding="utf-8")
        operations = _operations(skill_root)
        readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")

        self.assertIn("references/doctor.md", skill)
        self.assertIn("Installed implementation repair", doctor)
        self.assertIn(
            "Repository tests, release audits, Mission Control checks, and codebase review remain",
            doctor,
        )
        self.assertIn("capability-contract version and required behavior markers", doctor)
        self.assertIn("bounded isolated hook smoke run", doctor)
        self.assertNotIn("Require the source checkout to pass its package test suite", doctor)
        self.assertIn("four or five non-terminal project-execution workers", doctor)
        self.assertIn("a newly recorded durable worker", doctor)
        self.assertIn("Time, `idle`, or `notLoaded` alone never proves", doctor)
        self.assertIn("UNATTENDED_RETURN_PATH", doctor)
        self.assertIn("verified absence of the required heartbeat", doctor)
        self.assertIn("zero-model structured-state scan", doctor)
        self.assertIn("coverage.reviewOnly", doctor)
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
        self.assertEqual(contract["contractVersion"], 21)
        self.assertEqual(
            contract["capabilities"]["missionControlLifecycle"],
            "bundled-autostart-user-disable-chat-control",
        )
        self.assertEqual(
            contract["capabilities"]["doctorDiagnostics"],
            "json-with-optional-mermaid",
        )
        self.assertEqual(
            contract["capabilities"]["doctorProjectScan"],
            "deterministic-structured-state-zero-model",
        )
        self.assertEqual(
            contract["capabilities"]["doctorSemanticReview"],
            "user-triggered-allowlisted-low-candidate-only",
        )
        self.assertEqual(contract["capabilities"]["reasoningDefault"], "low-or-medium")
        self.assertEqual(
            contract["capabilities"]["registrationDelivery"],
            "document-only-no-ack",
        )
        self.assertEqual(contract["capabilities"]["subagents"], "allowed-parent-owned")
        self.assertEqual(
            contract["capabilities"]["workerGranularity"],
            "durable-complex-only",
        )
        self.assertEqual(
            contract["capabilities"]["microtaskExecution"],
            "current-owner-or-parent-subagent",
        )
        self.assertEqual(
            contract["capabilities"]["parallelWorkerTarget"],
            "one-to-three-default-five-max",
        )
        self.assertEqual(
            contract["capabilities"]["operationsGuidance"],
            "split-by-action-lane",
        )
        self.assertEqual(
            contract["capabilities"]["coordinationReadCache"],
            "two-phase-inbox-hash-checkpoint",
        )
        self.assertEqual(
            contract["capabilities"]["nativeTaskReads"],
            "host-cursor-no-mirror",
        )
        self.assertEqual(
            contract["capabilities"]["continuationGuarantee"],
            "verified-return-path-before-final",
        )
        self.assertEqual(
            contract["capabilities"]["archivedRecovery"],
            "direct-request-no-repeat-confirmation",
        )
        self.assertEqual(
            contract["capabilities"]["externalWriteDisclosure"],
            "prewrite-notice-and-scope-authority",
        )
        self.assertEqual(
            contract["capabilities"]["subagentDispatch"],
            "one-to-three-for-two-independent-lanes",
        )
        self.assertEqual(
            contract["capabilities"]["pythonRuntimeBootstrap"],
            "bounded-machine-discovery-informed-install",
        )
        self.assertEqual(
            contract["capabilities"]["lifecycleCleanup"],
            "dry-run-first-history-preserving",
        )
        self.assertEqual(
            contract["capabilities"]["globalUninstall"],
            "verified-project-index-no-drive-scan",
        )
        self.assertEqual(
            contract["capabilities"]["worktreeSelection"],
            "coordinator-selected-bounded-when-beneficial",
        )
        self.assertEqual(
            contract["capabilities"]["waitingClassification"],
            "canonical-evidence-only",
        )
        self.assertEqual(
            contract["capabilities"]["delegationDecision"],
            "reuse-first-recorded",
        )
        self.assertEqual(
            contract["capabilities"]["taskTitlePolicy"],
            "rename-generic-once-preserve-user-title",
        )
        self.assertEqual(
            contract["capabilities"]["historicalTaskReconciliation"],
            "current-goal-authority-and-disposition",
        )
        self.assertTrue((skill_root / "scripts" / "coordination_state.py").is_file())


if __name__ == "__main__":
    unittest.main()
