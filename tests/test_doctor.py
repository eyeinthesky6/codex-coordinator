from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
DOCTOR_PATH = (
    REPOSITORY
    / "plugins"
    / "codex-coordinator"
    / "scripts"
    / "codex_coordinator_doctor.py"
)
SPEC = importlib.util.spec_from_file_location("codex_coordinator_doctor", DOCTOR_PATH)
assert SPEC and SPEC.loader
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)

SKILL_TEXT = """---
name: codex-coordinator
description: Test fixture
---

# Source skill

Read the short [operations index](references/operations.md).

Coordinator is control-first by default.
Use one repository heartbeat.
Before the final answer, verify exactly one repository heartbeat.
Every same-repository Codex task is managed by default.
Only a direct user instruction may add or remove an exclusion.
A user pause switches to `REPORT_ONLY`.
workload idle never unregisters the Coordinator.
The original direct user request supplies this creation authority.
For every generated task, set reasoning explicitly to `low` or `medium`.
Subagents remain available as parent-owned helpers.
Use one to three parent-owned subagents when two or more independent, bounded lanes can shorten the turn.
Do not spawn them for a single trivial command.
Apply the durable-thread gate before creating a user-visible worker.
Before retaining implementation, record the reuse-first choice.
A coordinated goal authorises one rename of a generated generic task title.
Task registration, acceptance, ownership recording, and permission-to-continue confirmations are document-only.
Use scripts/coordination_state.py.
Use the two-phase inbox hash checkpoint.
Full filesystem access is capability, not user authority.
Before the first intentional write in a turn outside the current Git common repository, notify the user.
Deactivation and normal uninstall are dry-run-first and preserve project history.
Mark unclear relevance or authority `AWAITING_USER_DECISION`.
In the update, count material historical items closed, continued, deferred or not needed.
At goal start, after material Git changes, and before closure, inspect provider state.
Any provider mutation requires exact current user consent.
At goal start, after material task or automation changes, and before closure, inspect scheduled work.
Before every user-visible Coordinator final response, reconcile the complete goal ledger.
"""

OPERATIONS_TEXT = """# Source operations

Read [execution.md](execution.md), read [reconciliation.md](reconciliation.md),
and read [messaging.md](messaging.md) only when selected.
Never cache codebase reads.
"""

EXECUTION_TEXT = """# Source execution

Put the complete executable assignment in the native creation prompt.
Subagents remain available inside a registered task.
Inherit the user's configured model, but use cost-safe reasoning.
Pass native thinking or the host's equivalent reasoning field as low or medium.
Routine microtasks stay inside the current owner or a parent-owned subagent.
Use one to three parent-owned subagents when at least two independent, bounded lanes can shorten the turn.
Do not use a lane when its coordination cost exceeds its value.
Record the delegation decision before ordinary implementation starts.
Rename a generated generic title once.
The Coordinator may place an independent writer in a bounded linked worktree.
Carry forward the exact unmet outcome.
Do not make the user inspect old task windows.
"""

RECONCILIATION_TEXT = """# Source reconciliation

Use scan-inbox and ack-inbox as a two-phase checkpoint.
Use afterCursor when native tasks expose it. Do not persist or mirror native turns.
Use codex_app__automation_update, codex_app__set_thread_pinned,
codex_app__set_thread_archived, codex_app__fork_thread, and
codex_app__handoff_thread.
Never send task registration, acceptance, task-ID assignment, ownership confirmation, or permission-to-continue messages.
Apply the End-of-turn continuation gate before the Coordinator final answer.
Apply GitHub monitoring and provider consent.
Require exact current user consent and return the exact provider receipt.
Apply Project-related scheduled-task reconciliation.
Record a direct user decision before any major scheduled-task change.
Before every user-visible Coordinator final response, report done work, pending work, blockers or decisions, next actions, and the full-goal verdict.
"""

MESSAGING_TEXT = """# Source messaging

Project-bound routing uses the Native task messenger.
Pass only the plain internal message body.
Never include or synthesize `<codex_delegation>` tags.
`CREATE_TASK` and `COMPLETE_ACK` are not cross-task message types.
Never switch to the collaboration messenger as a fallback.
"""

DOCTOR_TEXT = """# Source doctor

Report UNATTENDED_RETURN_PATH only after verified absence of the required heartbeat.
Routine Doctor never receives project paths, task URLs, transcript text, or application files.
Deep Review is never scheduled and its result is candidate-only.
Use an immutable package receipt for managed files.
Never rewrite marketplace-managed cache files.
Restore last-known-good files after a failed manual repair.
"""

RECOVERY_TEXT = """# Source recovery

Always inspect that exact owner's native status in the same turn.
When archived, never ask the user to ping the old task, repeat an exact phrase, or approve replacement again.
The direct request that first exposes the archived owner is sufficient recovery authority.
"""

MAINTENANCE_TEXT = """# Source maintenance

Before an installation, repair, or Doctor `--apply` writes outside the current repository, notify the user.
A user-approved recurring Doctor may reuse the bounded project inbox targets already disclosed.
Newly discovered projects or external destinations require a fresh notice and approval.

## Deactivation, uninstall, and purge

Run global-plan --codex-home <codex-home>. The helper never scans an entire drive.
"""

INSTALLATION_TEXT = """# Source installation

## Project deactivation and reactivation

Run project deactivate --project-root <primary-worktree> as a dry run.
Run project reactivate --project-root <primary-worktree> as a dry run.
Project purge is not opt-out.
"""


def _source_plugin(root: Path, *, name: str = "codex-coordinator") -> Path:
    plugin = root / "plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / "hooks").mkdir()
    (plugin / "scripts").mkdir()
    (plugin / "skills" / "codex-coordinator" / "references").mkdir(parents=True)
    (plugin / "skills" / "codex-coordinator" / "scripts").mkdir()
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "name": name,
                "version": "1.0.0",
                doctor.PACKAGE_STATE_KEY: doctor.RELEASE_PACKAGE_STATE,
                doctor.RECEIPT_MANIFEST_KEY: "release-receipt.json",
            }
        ),
        encoding="utf-8",
    )
    (plugin / "hooks" / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "command": "python3 ${PLUGIN_ROOT}/scripts/codex_coordinator_session_start.py"
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (plugin / "scripts" / "codex_coordinator_session_start.py").write_text(
        "import json, sys\njson.load(sys.stdin)\n", encoding="utf-8"
    )
    skill = plugin / "skills" / "codex-coordinator"
    (skill / "SKILL.md").write_text(SKILL_TEXT, encoding="utf-8")
    (skill / "references" / "operations.md").write_text(OPERATIONS_TEXT, encoding="utf-8")
    (skill / "references" / "execution.md").write_text(EXECUTION_TEXT, encoding="utf-8")
    (skill / "references" / "reconciliation.md").write_text(
        RECONCILIATION_TEXT, encoding="utf-8"
    )
    (skill / "references" / "messaging.md").write_text(MESSAGING_TEXT, encoding="utf-8")
    (skill / "references" / "doctor.md").write_text(DOCTOR_TEXT, encoding="utf-8")
    (skill / "references" / "recovery.md").write_text(RECOVERY_TEXT, encoding="utf-8")
    (skill / "references" / "maintenance.md").write_text(
        MAINTENANCE_TEXT, encoding="utf-8"
    )
    (skill / "references" / "installation.md").write_text(
        INSTALLATION_TEXT, encoding="utf-8"
    )
    (skill / "scripts" / "coordination_state.py").write_text(
        "def main():\n    return 0\n", encoding="utf-8"
    )
    (skill / "scripts" / "__pycache__").mkdir()
    (skill / "scripts" / "__pycache__" / "coordination_state.pyc").write_bytes(b"cache")
    (skill / doctor.CAPABILITY_CONTRACT).write_text(
        json.dumps(
            {
                "contractVersion": doctor.CAPABILITY_CONTRACT_VERSION,
                "capabilities": {
                    **doctor.REQUIRED_CAPABILITIES,
                    "taskLifecycle": sorted(doctor.REQUIRED_TASK_LIFECYCLE),
                },
            }
        ),
        encoding="utf-8",
    )
    managed_files = []
    for source in sorted(skill.rglob("*")):
        relative = source.relative_to(skill)
        if (
            not source.is_file()
            or "__pycache__" in relative.parts
            or source.suffix.lower() in {".pyc", ".pyo"}
        ):
            continue
        managed_files.append(
            {
                "kind": "skill",
                "sourcePath": source.relative_to(plugin).as_posix(),
                "managedPath": relative.as_posix(),
                "sha256": doctor._sha256(source.read_bytes()),
            }
        )
    hook = plugin / "scripts" / doctor.HOOK_NAME
    managed_files.append(
        {
            "kind": "hook",
            "sourcePath": hook.relative_to(plugin).as_posix(),
            "managedPath": doctor.HOOK_NAME,
            "sha256": doctor._sha256(hook.read_bytes()),
        }
    )
    (plugin / "release-receipt.json").write_text(
        json.dumps(
            {
                "schemaVersion": doctor.RECEIPT_SCHEMA_VERSION,
                "pluginName": name,
                "packageVersion": "1.0.0",
                doctor.PACKAGE_STATE_KEY: doctor.RELEASE_PACKAGE_STATE,
                "packageId": (
                    f"{doctor.PLUGIN_NAME}-package@1.0.0"
                    f"+contract{doctor.CAPABILITY_CONTRACT_VERSION}"
                ),
                "managedFiles": managed_files,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return plugin


def _refresh_receipt(plugin: Path) -> None:
    receipt_path = plugin / "release-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for entry in receipt["managedFiles"]:
        source = plugin / entry["sourcePath"]
        entry["sha256"] = doctor._sha256(source.read_bytes())
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")


def _release_identity(plugin: Path) -> dict[str, str]:
    manifest = json.loads(
        (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    return {
        "expected_package_version": manifest["version"],
        "expected_receipt_sha256": doctor._sha256(
            (plugin / "release-receipt.json").read_bytes()
        ),
    }


def _sync_installation(
    source: Path,
    skill_root: Path,
    hook_path: Path,
    **kwargs: object,
) -> dict[str, object]:
    identity = _release_identity(source)
    for key, value in identity.items():
        kwargs.setdefault(key, value)
    return doctor.sync_installation(source, skill_root, hook_path, **kwargs)


class DoctorTests(unittest.TestCase):
    def test_mermaid_projection_shows_verified_states_without_private_paths(self) -> None:
        report = {
            "status": "drift",
            "changedFiles": 1,
            "skillRoot": "C:/Users/example/.agents/skills/codex-coordinator",
            "hookPath": "C:/Users/example/.codex/hooks/session_start.py",
            "files": [
                {
                    "kind": "skill",
                    "managedPath": "references/operations.md",
                    "target": "C:/Users/example/.agents/skills/codex-coordinator/references/operations.md",
                    "state": "drift",
                },
                {
                    "kind": "hook",
                    "managedPath": "codex_coordinator_session_start.py",
                    "target": "C:/Users/example/.codex/hooks/session_start.py",
                    "state": "current",
                },
            ],
            "installationChecks": [],
        }

        diagram = doctor.render_mermaid(report)

        self.assertIn("references/operations.md<br/>DRIFT", diagram)
        self.assertIn("codex_coordinator_session_start.py<br/>CURRENT", diagram)
        self.assertIn("DRIFT<br/>1 managed file(s) differ", diagram)
        self.assertNotIn("C:/Users/example", diagram)

    def test_cli_writes_mermaid_projection_for_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hooks" / "session_start.py"
            diagram_path = root / "reports" / "doctor.mmd"
            identity = _release_identity(source)

            with mock.patch("builtins.print") as print_output:
                result = doctor.main(
                    [
                        "--source-plugin",
                        str(source),
                        "--skill-root",
                        str(skill_root),
                        "--hook-path",
                        str(hook_path),
                        "--expected-package-version",
                        identity["expected_package_version"],
                        "--expected-receipt-sha256",
                        identity["expected_receipt_sha256"],
                        "--check",
                        "--mermaid-out",
                        str(diagram_path),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertTrue(diagram_path.is_file())
            self.assertIn("MISSING", diagram_path.read_text(encoding="utf-8"))
            payload = json.loads(print_output.call_args.args[0])
            self.assertEqual(payload["mermaidPath"], str(diagram_path.resolve()))
            self.assertIn("Visual projection only", payload["mermaidNote"])

    def test_compact_cli_omits_paths_and_file_details(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hooks" / "session_start.py"
            identity = _release_identity(source)

            with mock.patch("builtins.print") as print_output:
                result = doctor.main(
                    [
                        "--source-plugin",
                        str(source),
                        "--skill-root",
                        str(skill_root),
                        "--hook-path",
                        str(hook_path),
                        "--expected-package-version",
                        identity["expected_package_version"],
                        "--expected-receipt-sha256",
                        identity["expected_receipt_sha256"],
                        "--compact",
                        "--check",
                    ]
                )

            self.assertEqual(result, 2)
            raw = print_output.call_args.args[0]
            self.assertLess(len(raw.encode("utf-8")), 200)
            payload = json.loads(raw)
            self.assertEqual(
                set(payload),
                {
                    "status",
                    "integrityState",
                    "recoveryState",
                    "changedFiles",
                    "checksPassed",
                },
            )
            self.assertNotIn(str(root), raw)

    def test_check_apply_and_repeat_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hooks" / "session_start.py"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("# Old skill\n", encoding="utf-8")
            (skill_root / "local-note.md").write_text(
                "preserve me even with [a local broken link](missing-local-file.md)\n",
                encoding="utf-8",
            )

            check = _sync_installation(source, skill_root, hook_path, apply=False)
            self.assertEqual(check["status"], "drift")
            self.assertEqual(check["integrityState"], "local_modification_detected")
            self.assertEqual(check["recoveryState"], "trusted_repair_available")
            self.assertEqual(check["changedFiles"], 12)

            applied = _sync_installation(source, skill_root, hook_path, apply=True)
            self.assertEqual(applied["status"], "updated")
            self.assertEqual(applied["recoveryState"], "repaired")
            self.assertEqual(
                (skill_root / "SKILL.md").read_text(encoding="utf-8"),
                SKILL_TEXT,
            )
            self.assertEqual(
                (skill_root / "references" / "operations.md").read_text(encoding="utf-8"),
                OPERATIONS_TEXT,
            )
            self.assertEqual(
                hook_path.read_text(encoding="utf-8"),
                "import json, sys\njson.load(sys.stdin)\n",
            )
            self.assertTrue((skill_root / "local-note.md").is_file())
            self.assertEqual(
                [check["name"] for check in applied["installationChecks"]],
                [
                    "skill-capability-contract",
                    "state-helper-syntax",
                    "skill-frontmatter",
                    "skill-links",
                    "hook-syntax",
                    "hook-smoke",
                ],
            )

            current = _sync_installation(source, skill_root, hook_path, apply=False)
            self.assertEqual(current["status"], "current")
            self.assertEqual(current["integrityState"], "healthy")
            self.assertEqual(current["changedFiles"], 0)

    def test_stale_policy_installation_is_repaired_without_project_or_unmanaged_writes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hooks" / "session_start.py"
            project_state = root / "project" / ".codex" / "coordination" / "CURRENT.md"
            project_state.parent.mkdir(parents=True)
            project_state.write_text("preserve project state\n", encoding="utf-8")

            initial = _sync_installation(source, skill_root, hook_path, apply=True)
            self.assertEqual(initial["status"], "updated")
            hook_before = hook_path.read_bytes()
            unmanaged = skill_root / "local-note.md"
            unmanaged.write_text("preserve unmanaged file\n", encoding="utf-8")

            contract_path = skill_root / doctor.CAPABILITY_CONTRACT
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["contractVersion"] = doctor.CAPABILITY_CONTRACT_VERSION - 1
            for name in (
                "deliverySummary",
                "providerMonitoring",
                "providerMutationConsent",
                "scheduledTaskReconciliation",
            ):
                contract["capabilities"].pop(name)
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            skill_path = skill_root / "SKILL.md"
            skill_path.write_text(
                skill_path.read_text(encoding="utf-8").replace(
                    "Any provider mutation requires exact current user consent.",
                    "Provider changes follow local convention.",
                ),
                encoding="utf-8",
            )
            reconciliation_path = skill_root / "references" / "reconciliation.md"
            reconciliation_path.write_text(
                reconciliation_path.read_text(encoding="utf-8").replace(
                    "Record a direct user decision before any major scheduled-task change.",
                    "Scheduled tasks may be changed when useful.",
                ),
                encoding="utf-8",
            )

            check = _sync_installation(source, skill_root, hook_path, apply=False)
            self.assertEqual(check["status"], "drift")
            self.assertEqual(check["changedFiles"], 3)
            self.assertEqual(check["installationChecks"], [])
            self.assertEqual(
                project_state.read_text(encoding="utf-8"), "preserve project state\n"
            )
            self.assertEqual(unmanaged.read_text(encoding="utf-8"), "preserve unmanaged file\n")
            self.assertEqual(hook_path.read_bytes(), hook_before)

            applied = _sync_installation(source, skill_root, hook_path, apply=True)
            self.assertEqual(applied["status"], "updated")
            self.assertEqual(applied["changedFiles"], 3)
            self.assertEqual(
                {
                    item["managedPath"]
                    for item in applied["files"]
                    if item["state"] == "updated"
                },
                {"SKILL.md", "capabilities.json", "references/reconciliation.md"},
            )
            self.assertEqual(
                project_state.read_text(encoding="utf-8"), "preserve project state\n"
            )
            self.assertEqual(unmanaged.read_text(encoding="utf-8"), "preserve unmanaged file\n")
            self.assertEqual(hook_path.read_bytes(), hook_before)
            repaired_contract = json.loads(contract_path.read_text(encoding="utf-8"))
            self.assertEqual(
                repaired_contract["contractVersion"], doctor.CAPABILITY_CONTRACT_VERSION
            )
            for name, expected in doctor.REQUIRED_CAPABILITIES.items():
                self.assertEqual(repaired_contract["capabilities"][name], expected)

            current = _sync_installation(source, skill_root, hook_path, apply=False)
            self.assertEqual(current["status"], "current")
            self.assertEqual(current["changedFiles"], 0)

    def test_missing_managed_file_is_detected_from_the_trusted_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            (skill_root / "references" / "operations.md").unlink()

            report = _sync_installation(source, skill_root, hook_path, apply=False)

            self.assertEqual(report["status"], "drift")
            self.assertEqual(report["integrityState"], "local_modification_detected")
            missing = [item for item in report["files"] if item["before"] == "missing"]
            self.assertEqual(
                [item["managedPath"] for item in missing],
                ["references/operations.md"],
            )

    def test_tampered_package_receipt_is_untrusted_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            receipt_path = source / "release-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["managedFiles"][0]["sha256"] = "0" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with self.assertRaisesRegex(doctor.DoctorError, "receipt hash mismatch"):
                _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_manual_package_requires_complete_external_release_identity_before_source_validation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with mock.patch.object(doctor, "_validated_source") as validate_source:
                with self.assertRaisesRegex(doctor.DoctorError, "requires both"):
                    doctor.sync_installation(
                        source,
                        skill_root,
                        hook_path,
                        apply=True,
                        installation_kind="manual",
                    )

            validate_source.assert_not_called()
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_malformed_external_release_pin_fails_before_target_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with mock.patch.object(doctor, "_validated_source") as validate_source:
                with self.assertRaisesRegex(doctor.DoctorError, "SHA-256 is malformed"):
                    doctor.sync_installation(
                        source,
                        skill_root,
                        hook_path,
                        apply=True,
                        installation_kind="manual",
                        expected_package_version="1.0.0",
                        expected_receipt_sha256="not-a-sha256",
                    )

            validate_source.assert_not_called()
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_malformed_expected_version_fails_before_target_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with mock.patch.object(doctor, "_validated_source") as validate_source:
                with self.assertRaisesRegex(doctor.DoctorError, "version is malformed"):
                    doctor.sync_installation(
                        source,
                        skill_root,
                        hook_path,
                        apply=True,
                        installation_kind="manual",
                        expected_package_version="not-a-version",
                        expected_receipt_sha256=_release_identity(source)[
                            "expected_receipt_sha256"
                        ],
                    )

            validate_source.assert_not_called()
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_wrong_release_pin_fails_without_installation_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with mock.patch.object(doctor, "_installation_kind") as classify_target:
                with self.assertRaisesRegex(doctor.DoctorError, "expected release pin"):
                    doctor.sync_installation(
                        source,
                        skill_root,
                        hook_path,
                        apply=True,
                        installation_kind="manual",
                        expected_package_version="1.0.0",
                        expected_receipt_sha256="0" * 64,
                    )

            classify_target.assert_not_called()
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_wrong_expected_version_fails_without_installation_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with self.assertRaisesRegex(doctor.DoctorError, "expected release version"):
                doctor.sync_installation(
                    source,
                    skill_root,
                    hook_path,
                    apply=True,
                    installation_kind="manual",
                    expected_package_version="2.0.0",
                    expected_receipt_sha256=_release_identity(source)[
                        "expected_receipt_sha256"
                    ],
                )

            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_wrong_release_identity_fails_without_installation_target_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            receipt_path = source / "release-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["packageId"] = "codex-coordinator-package@another-release"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with mock.patch.object(doctor, "_installation_kind") as classify_target:
                with self.assertRaisesRegex(doctor.DoctorError, "wrong release identity"):
                    doctor.sync_installation(
                        source,
                        skill_root,
                        hook_path,
                        apply=True,
                        installation_kind="manual",
                        **_release_identity(source),
                    )

            classify_target.assert_not_called()
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_regenerated_malicious_receipt_fails_against_prior_external_pin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            identity = _release_identity(source)
            (source / "skills" / "codex-coordinator" / "SKILL.md").write_text(
                "# regenerated malicious package\n", encoding="utf-8"
            )
            _refresh_receipt(source)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with self.assertRaisesRegex(doctor.DoctorError, "expected release pin"):
                doctor.sync_installation(
                    source,
                    skill_root,
                    hook_path,
                    apply=True,
                    installation_kind="manual",
                    **identity,
                )

            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_legitimate_repackaged_bytes_install_with_new_external_pin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill = source / "skills" / "codex-coordinator" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            _refresh_receipt(source)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            report = doctor.sync_installation(
                source,
                skill_root,
                hook_path,
                apply=True,
                installation_kind="manual",
                **_release_identity(source),
            )

            self.assertEqual(report["status"], "updated")
            self.assertEqual(
                (skill_root / "SKILL.md").read_bytes(), skill.read_bytes()
            )

    def test_development_package_is_not_a_manual_repair_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            manifest_path = source / ".codex-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest[doctor.PACKAGE_STATE_KEY] = "development"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with self.assertRaisesRegex(doctor.DoctorError, "not a release package"):
                doctor.sync_installation(
                    source,
                    skill_root,
                    hook_path,
                    apply=True,
                    installation_kind="manual",
                    **_release_identity(source),
                )

            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_dirty_developer_source_is_not_a_trusted_repair_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            completed = subprocess.run(
                ["git", "init", str(root)],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            with self.assertRaisesRegex(doctor.DoctorError, "dirty developer checkout"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=True,
                )

    def test_marketplace_managed_target_requires_supported_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            plugin_cache = root / "codex-home" / "plugins" / "cache" / "coordinator"
            skill_root = plugin_cache / "skills" / "codex-coordinator"
            hook_path = plugin_cache / "scripts" / doctor.HOOK_NAME

            report = doctor.sync_installation(
                source,
                skill_root,
                hook_path,
                apply=True,
            )

            self.assertEqual(report["status"], "drift")
            self.assertEqual(report["recoveryState"], "reinstall_required")
            self.assertEqual(report["installationKind"], "marketplace")
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())
            self.assertIn("plugin update or reinstall", report["note"])

    def test_modified_marketplace_package_fails_closed_to_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "codex-home" / "plugins" / "cache"
            source = _source_plugin(cache)
            (source / "skills" / "codex-coordinator" / "SKILL.md").write_text(
                "locally modified cache\n", encoding="utf-8"
            )
            skill_root = root / "manual" / "skill"
            hook_path = root / "manual" / "hook.py"

            report = doctor.sync_installation(
                source,
                skill_root,
                hook_path,
                apply=True,
            )

            self.assertEqual(report["status"], "error")
            self.assertEqual(report["recoveryState"], "reinstall_required")
            self.assertEqual(report["installationKind"], "marketplace")
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_wrong_plugin_source_is_rejected_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root, name="another-plugin")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with self.assertRaises(doctor.DoctorError):
                _sync_installation(source, skill_root, hook_path, apply=True)
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_hook_destination_cannot_overlap_the_installed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = skill_root / "scripts" / "coordination_state.py"

            with self.assertRaisesRegex(doctor.DoctorError, "overlap"):
                _sync_installation(source, skill_root, hook_path, apply=True)
            self.assertFalse(skill_root.exists())

    def test_installed_skill_cannot_be_nested_under_hook_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            hook_path = root / "installed" / "hook.py"
            skill_root = hook_path / "skill"

            with self.assertRaisesRegex(doctor.DoctorError, "overlap"):
                _sync_installation(source, skill_root, hook_path, apply=True)
            self.assertFalse(hook_path.exists())

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            manifest = source / ".codex-plugin" / "plugin.json"
            manifest.write_text(
                '{"name":"wrong","name":"codex-coordinator","version":"1.0.0"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(doctor.DoctorError, "Duplicate JSON key.*name"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=False,
                )

    def test_lookalike_hook_registration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            (source / "hooks" / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "note": doctor.HOOK_NAME,
                                    "hooks": [
                                        {
                                            "command": "python3 ${PLUGIN_ROOT}/scripts/unrelated.py"
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(doctor.DoctorError):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=True,
                )

    def test_later_write_failure_restores_every_earlier_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hooks" / "session_start.py"
            (skill_root / "references").mkdir(parents=True)
            hook_path.parent.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("# Old skill\n", encoding="utf-8")
            (skill_root / "references" / "operations.md").write_text(
                "# Old operations\n", encoding="utf-8"
            )
            hook_path.write_text("print('old hook')\n", encoding="utf-8")
            original_write = doctor._atomic_write
            writes = 0

            def fail_second_write(path: Path, data: bytes) -> None:
                nonlocal writes
                writes += 1
                if writes == 2:
                    raise OSError("simulated later write failure")
                original_write(path, data)

            with mock.patch.object(doctor, "_atomic_write", side_effect=fail_second_write):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(
                failure.exception.report["recoveryState"],
                "repair_failed_last_good_restored",
            )
            self.assertTrue(failure.exception.report["rollback"]["lastGoodRestored"])

            self.assertEqual(
                (skill_root / "SKILL.md").read_text(encoding="utf-8"), "# Old skill\n"
            )
            self.assertEqual(
                (skill_root / "references" / "operations.md").read_text(encoding="utf-8"),
                "# Old operations\n",
            )
            self.assertEqual(hook_path.read_text(encoding="utf-8"), "print('old hook')\n")

    def test_failed_last_good_restore_requires_manual_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            (skill_root / "agents").mkdir(parents=True)
            (skill_root / "agents" / "openai.yaml").write_text(
                "old agent metadata\n", encoding="utf-8"
            )
            (skill_root / "SKILL.md").write_text("# Old skill\n", encoding="utf-8")
            hook_path.parent.mkdir(parents=True, exist_ok=True)
            hook_path.write_text("print('old hook')\n", encoding="utf-8")
            original_write = doctor._atomic_write
            writes = 0

            def fail_update_and_restore(path: Path, data: bytes) -> None:
                nonlocal writes
                writes += 1
                if writes in {2, 3}:
                    raise OSError("simulated update or restore failure")
                original_write(path, data)

            with mock.patch.object(
                doctor, "_atomic_write", side_effect=fail_update_and_restore
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(
                failure.exception.report["recoveryState"], "manual_action_required"
            )
            self.assertFalse(failure.exception.report["rollback"]["lastGoodRestored"])
            self.assertEqual(len(failure.exception.report["rollback"]["errors"]), 1)

    def test_installed_runtime_failure_rolls_back_the_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            (source / "scripts" / doctor.HOOK_NAME).write_text(
                "raise SystemExit(7)\n", encoding="utf-8"
            )
            _refresh_receipt(source)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            (skill_root / "references").mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("# Old skill\n", encoding="utf-8")
            (skill_root / "references" / "operations.md").write_text(
                "# Old operations\n", encoding="utf-8"
            )
            hook_path.write_text("print('old hook')\n", encoding="utf-8")

            with self.assertRaises(doctor.RepairFailed) as failure:
                _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertIn("smoke check failed", failure.exception.report["error"])
            self.assertEqual(
                failure.exception.report["recoveryState"],
                "repair_failed_last_good_restored",
            )

            self.assertEqual(
                (skill_root / "SKILL.md").read_text(encoding="utf-8"), "# Old skill\n"
            )
            self.assertEqual(hook_path.read_text(encoding="utf-8"), "print('old hook')\n")

    def test_stale_capability_contract_is_rejected_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            contract = source / "skills" / "codex-coordinator" / doctor.CAPABILITY_CONTRACT
            value = json.loads(contract.read_text(encoding="utf-8"))
            value["capabilities"]["workerCreation"] = "holding-turn"
            contract.write_text(json.dumps(value), encoding="utf-8")

            with self.assertRaisesRegex(doctor.DoctorError, "workerCreation.*stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=True,
                )

    def test_provider_delivery_and_scheduled_capabilities_are_required_before_installation(
        self,
    ) -> None:
        for name in (
            "deliverySummary",
            "providerMonitoring",
            "providerMutationConsent",
            "scheduledTaskReconciliation",
        ):
            with self.subTest(capability=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = _source_plugin(root)
                contract = (
                    source
                    / "skills"
                    / "codex-coordinator"
                    / doctor.CAPABILITY_CONTRACT
                )
                value = json.loads(contract.read_text(encoding="utf-8"))
                value["capabilities"].pop(name)
                contract.write_text(json.dumps(value), encoding="utf-8")

                with self.assertRaisesRegex(doctor.DoctorError, rf"{name}.*stale"):
                    _sync_installation(
                        source,
                        root / "installed" / "skill",
                        root / "installed" / "hook.py",
                        apply=True,
                    )

    def test_provider_delivery_and_scheduled_guidance_markers_are_required(self) -> None:
        cases = (
            ("SKILL.md", "At goal start, after material Git changes, and before closure"),
            ("SKILL.md", "Any provider mutation requires exact current user consent."),
            (
                "SKILL.md",
                "At goal start, after material task or automation changes, and before closure",
            ),
            ("SKILL.md", "Before every user-visible Coordinator final response"),
            (
                "references/reconciliation.md",
                "GitHub monitoring and provider consent",
            ),
            ("references/reconciliation.md", "exact current user consent"),
            ("references/reconciliation.md", "return the exact provider receipt"),
            (
                "references/reconciliation.md",
                "Project-related scheduled-task reconciliation",
            ),
            (
                "references/reconciliation.md",
                "Record a direct user decision before any major scheduled-task change.",
            ),
            (
                "references/reconciliation.md",
                "Before every user-visible Coordinator final response",
            ),
            (
                "references/reconciliation.md",
                "done work, pending work, blockers or decisions, next actions, and the full-goal verdict",
            ),
        )
        for relative, marker in cases:
            with self.subTest(
                relative=relative, marker=marker
            ), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = _source_plugin(root)
                guidance = source / "skills" / "codex-coordinator" / relative
                guidance.write_text(
                    guidance.read_text(encoding="utf-8").replace(marker, "stale guidance"),
                    encoding="utf-8",
                )

                with self.assertRaisesRegex(doctor.DoctorError, "guidance is stale"):
                    _sync_installation(
                        source,
                        root / "installed" / "skill",
                        root / "installed" / "hook.py",
                        apply=False,
                    )

    def test_inherited_reasoning_default_is_rejected_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            contract = source / "skills" / "codex-coordinator" / doctor.CAPABILITY_CONTRACT
            value = json.loads(contract.read_text(encoding="utf-8"))
            value["capabilities"]["reasoningDefault"] = "inherit"
            contract.write_text(json.dumps(value), encoding="utf-8")

            with self.assertRaisesRegex(doctor.DoctorError, "reasoningDefault.*stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=True,
                )

    def test_microtask_worker_policy_is_rejected_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            contract = source / "skills" / "codex-coordinator" / doctor.CAPABILITY_CONTRACT
            value = json.loads(contract.read_text(encoding="utf-8"))
            value["capabilities"]["workerGranularity"] = "one-thread-per-check"
            contract.write_text(json.dumps(value), encoding="utf-8")

            with self.assertRaisesRegex(doctor.DoctorError, "workerGranularity.*stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=True,
                )

    def test_native_registration_ack_capability_is_rejected_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            contract = source / "skills" / "codex-coordinator" / doctor.CAPABILITY_CONTRACT
            value = json.loads(contract.read_text(encoding="utf-8"))
            value["capabilities"]["registrationDelivery"] = "native-ack"
            contract.write_text(json.dumps(value), encoding="utf-8")

            with self.assertRaisesRegex(doctor.DoctorError, "registrationDelivery.*stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=True,
                )

    def test_stale_operating_guidance_is_rejected_even_when_contract_claims_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            execution = source / "skills" / "codex-coordinator" / "references" / "execution.md"
            execution.write_text(
                EXECUTION_TEXT.replace(
                    "Put the complete executable assignment in the native creation prompt.",
                    "Create one non-executable holding prompt.",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(doctor.DoctorError, "guidance is stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=False,
                )

    def test_nested_native_message_guidance_is_required_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            messaging = (
                source / "skills" / "codex-coordinator" / "references" / "messaging.md"
            )
            messaging.write_text(
                MESSAGING_TEXT.replace(
                    "Never include or synthesize `<codex_delegation>` tags.",
                    "Wrap every prompt in a codex_delegation tag.",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(doctor.DoctorError, "guidance is stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=False,
                )

    def test_external_write_disclosure_is_required_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill = source / "skills" / "codex-coordinator" / "SKILL.md"
            skill.write_text(
                SKILL_TEXT.replace(
                    "Full filesystem access is capability, not user authority.\n",
                    "Full filesystem access authorises every write.\n",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(doctor.DoctorError, "guidance is stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=False,
                )

    def test_subagent_dispatch_threshold_is_required_before_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill = source / "skills" / "codex-coordinator" / "SKILL.md"
            skill.write_text(
                SKILL_TEXT.replace(
                    "Use one to three parent-owned subagents when two or more independent, bounded lanes can shorten the turn.\n",
                    "Always spawn as many subagents as possible.\n",
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(doctor.DoctorError, "guidance is stale"):
                _sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=False,
                )

if __name__ == "__main__":
    unittest.main()
