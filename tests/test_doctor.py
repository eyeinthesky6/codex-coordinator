from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shutil
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


def _redirect_directory(path: Path, target: Path) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(path), str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr or completed.stdout)
    else:
        path.symlink_to(target, target_is_directory=True)


def _remove_redirect_directory(path: Path) -> None:
    if os.name == "nt":
        path.rmdir()
    else:
        path.unlink()


class DoctorTests(unittest.TestCase):
    def test_hook_smoke_uses_the_same_isolated_import_boundary_as_startup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "shadow-executed.txt"
            (root / "json.py").write_text(
                "import os\n"
                "open(os.environ['CODEX_SHADOW_MARKER'], 'w', encoding='utf-8').write(__file__)\n"
                "raise RuntimeError('shadow json executed')\n",
                encoding="utf-8",
            )
            hook = (
                REPOSITORY
                / "plugins"
                / "codex-coordinator"
                / "scripts"
                / doctor.HOOK_NAME
            )
            environment = {
                "CODEX_COORDINATOR_DISABLE_MISSION_CONTROL_AUTOSTART": "1",
                "CODEX_SHADOW_MARKER": str(marker),
                "PYTHONPATH": str(root),
            }

            with mock.patch.object(
                doctor.tempfile,
                "TemporaryDirectory",
                return_value=contextlib.nullcontext(str(root)),
            ), mock.patch.dict(os.environ, environment, clear=False):
                checks = doctor._validate_installed_hook(hook)

            self.assertFalse(marker.exists())
            self.assertIn({"name": "hook-smoke", "status": "passed"}, checks)

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
                    "installationKind",
                    "changedFiles",
                    "checksPassed",
                },
            )
            self.assertNotIn(str(root), raw)

    @unittest.skipUnless(os.name == "nt", "manual repair requires handle-bound replace")
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

    @unittest.skipUnless(os.name == "nt", "manual repair requires handle-bound replace")
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

    @unittest.skipUnless(os.name == "nt", "manual repair setup requires handle-bound replace")
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
                apply=os.name == "nt",
                installation_kind="manual",
                **_release_identity(source),
            )

            if os.name == "nt":
                self.assertEqual(report["status"], "updated")
                self.assertEqual(
                    (skill_root / "SKILL.md").read_bytes(), skill.read_bytes()
                )
            else:
                self.assertEqual(report["status"], "drift")
                self.assertEqual(report["recoveryState"], "trusted_repair_available")

    def test_development_package_is_not_a_manual_repair_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            receipt_path = source / "release-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt[doctor.PACKAGE_STATE_KEY] = "development"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with self.assertRaisesRegex(doctor.DoctorError, "not a release receipt"):
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
                installation_kind="manual",
            )

            self.assertEqual(report["status"], "error")
            self.assertEqual(report["recoveryState"], "reinstall_required")
            self.assertEqual(report["installationKind"], "marketplace")
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())
            self.assertIn("plugin update or reinstall", report["note"])

    def test_explicit_manual_kind_cannot_override_marketplace_cache_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            plugin_cache = root / "codex-home" / "plugins" / "cache" / "coordinator"
            cases = (
                (
                    source,
                    plugin_cache / "skills" / "codex-coordinator",
                    plugin_cache / "scripts" / doctor.HOOK_NAME,
                ),
                (
                    _source_plugin(root / "source-cache" / "plugins" / "cache"),
                    root / "manual" / "skill",
                    root / "manual" / "hook.py",
                ),
            )

            for package, skill_root, hook_path in cases:
                with self.subTest(package=package, skill_root=skill_root):
                    report = doctor.sync_installation(
                        package,
                        skill_root,
                        hook_path,
                        apply=True,
                        installation_kind="manual",
                    )

                    self.assertEqual(report["status"], "error")
                    self.assertEqual(report["recoveryState"], "reinstall_required")
                    self.assertEqual(report["installationKind"], "marketplace")
                    self.assertFalse(skill_root.exists())
                    self.assertFalse(hook_path.exists())

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
                installation_kind="manual",
            )

            self.assertEqual(report["status"], "error")
            self.assertEqual(report["recoveryState"], "reinstall_required")
            self.assertEqual(report["installationKind"], "marketplace")
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_marketplace_matching_caller_pins_still_require_supported_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "codex-home" / "plugins" / "cache")
            skill_root = source / "skills" / "codex-coordinator"
            hook_path = source / "scripts" / doctor.HOOK_NAME

            with mock.patch.object(doctor, "_validated_source") as validate_source:
                report = doctor.sync_installation(
                    source,
                    skill_root,
                    hook_path,
                    apply=True,
                    installation_kind="marketplace",
                    **_release_identity(source),
                )

            self.assertEqual(report["status"], "error")
            self.assertNotEqual(report["integrityState"], "healthy")
            self.assertEqual(report["recoveryState"], "reinstall_required")
            self.assertEqual(report["installationKind"], "marketplace")
            self.assertEqual(report["changedFiles"], 0)
            validate_source.assert_not_called()

    def test_marketplace_missing_malformed_or_mismatched_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "codex-home" / "plugins" / "cache")
            skill_root = source / "skills" / "codex-coordinator"
            hook_path = source / "scripts" / doctor.HOOK_NAME
            cases = (
                ("missing", {}),
                (
                    "malformed",
                    {
                        "expected_package_version": "not-a-version",
                        "expected_receipt_sha256": "not-a-sha",
                    },
                ),
                (
                    "mismatch",
                    {
                        "expected_package_version": "9.9.9",
                        "expected_receipt_sha256": "0" * 64,
                    },
                ),
            )

            for label, identity in cases:
                with self.subTest(label=label), mock.patch.object(
                    doctor, "_InstalledTargetAccess"
                ) as target_access:
                    report = doctor.sync_installation(
                        source,
                        skill_root,
                        hook_path,
                        apply=True,
                        installation_kind="marketplace",
                        **identity,
                    )

                    self.assertEqual(report["status"], "error")
                    self.assertEqual(report["recoveryState"], "reinstall_required")
                    self.assertEqual(report["installationKind"], "marketplace")
                    self.assertEqual(report["changedFiles"], 0)
                    self.assertEqual(report["files"], [])
                    target_access.assert_not_called()

    def test_marketplace_package_and_receipt_cotamper_cannot_self_attest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "codex-home" / "plugins" / "cache")
            skill_root = source / "skills" / "codex-coordinator"
            hook_path = source / "scripts" / doctor.HOOK_NAME
            skill_path = skill_root / "SKILL.md"
            tampered = b"co-tampered package and receipt\n"
            skill_path.write_bytes(tampered)
            _refresh_receipt(source)
            recomputed_identity = _release_identity(source)

            with mock.patch.object(
                doctor, "_InstalledTargetAccess"
            ) as target_access, mock.patch.object(
                doctor, "_validated_source"
            ) as validate_source:
                report = doctor.sync_installation(
                    source,
                    skill_root,
                    hook_path,
                    apply=True,
                    installation_kind="marketplace",
                    **recomputed_identity,
                )

            self.assertEqual(report["status"], "error")
            self.assertNotEqual(report["integrityState"], "healthy")
            self.assertEqual(report["recoveryState"], "reinstall_required")
            self.assertEqual(report["installationKind"], "marketplace")
            self.assertEqual(report["changedFiles"], 0)
            self.assertEqual(report["files"], [])
            self.assertEqual(skill_path.read_bytes(), tampered)
            target_access.assert_not_called()
            validate_source.assert_not_called()

    def test_manifest_cannot_redirect_the_fixed_release_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            manifest_path = source / ".codex-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["integrityReceipt"] = "attacker-controlled-receipt.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (source / "attacker-controlled-receipt.json").write_text(
                json.dumps({"packageState": "release", "managedFiles": []}),
                encoding="utf-8",
            )

            _, _, trusted_receipt, _ = doctor._validated_source(
                source,
                expected_receipt_sha256=_release_identity(source)[
                    "expected_receipt_sha256"
                ],
                expected_package_version="1.0.0",
            )

            self.assertEqual(
                trusted_receipt["packageId"],
                f"{doctor.PLUGIN_NAME}-package@1.0.0"
                f"+contract{doctor.CAPABILITY_CONTRACT_VERSION}",
            )

    def test_runtime_receipt_rows_are_validated_but_never_install_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "plugin"
            shutil.copytree(
                REPOSITORY / "plugins" / "codex-coordinator",
                source,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            manifest = json.loads(
                (source / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
            )
            receipt_path = source / "release-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["packageState"] = "release"
            receipt["packageVersion"] = manifest["version"]
            receipt["packageId"] = (
                f"{doctor.PLUGIN_NAME}-package@{manifest['version']}"
                f"+contract{doctor.CAPABILITY_CONTRACT_VERSION}"
            )
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            identity = _release_identity(source)

            _skill, _hook, _summary, entries = doctor._validated_source(
                source,
                expected_receipt_sha256=identity["expected_receipt_sha256"],
                expected_package_version=identity["expected_package_version"],
            )

            self.assertTrue(any(item["kind"] == "runtime" for item in entries))
            self.assertTrue(
                all(item["kind"] in {"skill", "hook"} for item in doctor._source_files(entries))
            )

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

    @unittest.skipUnless(os.name == "nt", "Windows directory transaction regression")
    def test_windows_first_install_failure_removes_only_created_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "new" / "installed" / "skill"
            hook_path = root / "new" / "installed" / "scripts" / "hook.py"
            original_write = doctor._InstalledTargetAccess.atomic_write
            writes = 0

            def fail_second_write(access: object, path: Path, data: bytes) -> None:
                nonlocal writes
                writes += 1
                if writes == 2:
                    raise RuntimeError("simulated first-install partial failure")
                original_write(access, path, data)

            with mock.patch.object(
                doctor._InstalledTargetAccess, "atomic_write", new=fail_second_write
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertTrue(failure.exception.report["rollback"]["lastGoodRestored"])
            self.assertFalse((root / "new").exists())

            preexisting = root / "preexisting"
            preexisting.mkdir()
            skill_root = preexisting / "installed" / "skill"
            hook_path = preexisting / "installed" / "scripts" / "hook.py"
            writes = 0
            with mock.patch.object(
                doctor._InstalledTargetAccess, "atomic_write", new=fail_second_write
            ):
                with self.assertRaises(doctor.RepairFailed):
                    _sync_installation(source, skill_root, hook_path, apply=True)
            self.assertTrue(preexisting.is_dir())
            self.assertEqual(list(preexisting.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows directory transaction regression")
    def test_windows_created_directory_nonempty_swap_and_cleanup_are_unproven(self) -> None:
        cases = ("nonempty", "swap", "cleanup")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = _source_plugin(root / "source")
                skill_root = root / "installed" / "skill"
                hook_path = root / "installed" / "scripts" / "hook.py"
                original_write = doctor._InstalledTargetAccess.atomic_write
                original_rollback = doctor._InstalledTargetAccess.rollback_created_directories
                writes = 0

                def fail_after_first(access: object, path: Path, data: bytes) -> None:
                    nonlocal writes
                    writes += 1
                    if writes == 2:
                        scripts = hook_path.parent
                        if case == "nonempty":
                            (scripts / "unexpected.txt").write_text(
                                "preserve", encoding="utf-8"
                            )
                        elif case == "swap":
                            moved = root / "moved-scripts"
                            scripts.rename(moved)
                            scripts.mkdir()
                            (scripts / "replacement.txt").write_text(
                                "preserve", encoding="utf-8"
                            )
                        raise RuntimeError(f"simulated {case} rollback")
                    original_write(access, path, data)

                def fail_cleanup_identity(access: object) -> list[str]:
                    if case != "cleanup":
                        return original_rollback(access)
                    with mock.patch.object(
                        access,
                        "_windows_identity",
                        side_effect=OSError("simulated directory cleanup failure"),
                    ):
                        return original_rollback(access)

                with mock.patch.object(
                    doctor._InstalledTargetAccess, "atomic_write", new=fail_after_first
                ), mock.patch.object(
                    doctor._InstalledTargetAccess,
                    "rollback_created_directories",
                    new=fail_cleanup_identity,
                ):
                    with self.assertRaises(doctor.RepairFailed) as failure:
                        _sync_installation(source, skill_root, hook_path, apply=True)

                report = failure.exception.report
                self.assertEqual(report["recoveryState"], "manual_action_required")
                self.assertFalse(report["rollback"]["lastGoodRestored"])
                self.assertTrue(
                    any("created directory" in error for error in report["rollback"]["errors"])
                )
                if case == "nonempty":
                    self.assertEqual(
                        (hook_path.parent / "unexpected.txt").read_text(encoding="utf-8"),
                        "preserve",
                    )
                elif case == "swap":
                    self.assertEqual(
                        (hook_path.parent / "replacement.txt").read_text(encoding="utf-8"),
                        "preserve",
                    )

    @unittest.skipIf(os.name == "nt", "Unix directory transaction regression")
    def test_unix_created_directory_rollback_preserves_preexisting_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preexisting = root / "preexisting"
            preexisting.mkdir()
            skill_root = preexisting / "installed" / "skill"
            hook_path = preexisting / "hook.py"
            access = doctor._InstalledTargetAccess(skill_root, hook_path)
            access.begin_directory_transaction()
            target = skill_root / "references" / "file.txt"
            with access._unix_parent(target, create=True):
                pass
            self.assertEqual(access.rollback_created_directories(), [])
            self.assertTrue(preexisting.is_dir())
            self.assertEqual(list(preexisting.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "Unix directory transaction regression")
    def test_unix_created_directory_nonempty_swap_and_cleanup_are_unproven(self) -> None:
        for case in ("nonempty", "swap", "cleanup"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                skill_root = root / "installed" / "skill"
                hook_path = root / "hook.py"
                access = doctor._InstalledTargetAccess(skill_root, hook_path)
                access.begin_directory_transaction()
                created = skill_root / "references"
                with access._unix_parent(created / "file.txt", create=True):
                    pass
                if case == "nonempty":
                    (created / "unexpected.txt").write_text("preserve", encoding="utf-8")
                elif case == "swap":
                    moved = root / "moved-references"
                    created.rename(moved)
                    created.mkdir()
                    (created / "replacement.txt").write_text("preserve", encoding="utf-8")
                if case == "cleanup":
                    patch = mock.patch.object(
                        doctor.os,
                        "rmdir",
                        side_effect=OSError("simulated directory cleanup failure"),
                    )
                else:
                    patch = contextlib.nullcontext()
                with patch:
                    errors = access.rollback_created_directories()
                self.assertTrue(errors)
                self.assertTrue(any("created directory" in error for error in errors))
                if case == "nonempty":
                    self.assertEqual(
                        (created / "unexpected.txt").read_text(encoding="utf-8"),
                        "preserve",
                    )
                elif case == "swap":
                    self.assertEqual(
                        (created / "replacement.txt").read_text(encoding="utf-8"),
                        "preserve",
                    )

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_windows_junction_is_rejected_without_outside_read_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "installed" / "skill"
            skill_root.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            outside_target = outside / "coordination_state.py"
            outside_target.write_bytes(b"outside-original")
            _redirect_directory(skill_root / "scripts", outside)
            hook_path = root / "installed" / "hook.py"
            outside_reads: list[Path] = []
            original_read_bytes = Path.read_bytes

            def track_read(path: Path) -> bytes:
                try:
                    path.resolve(strict=False).relative_to(outside.resolve())
                except ValueError:
                    pass
                else:
                    outside_reads.append(path)
                return original_read_bytes(path)

            with mock.patch.object(Path, "read_bytes", track_read):
                with self.assertRaisesRegex(
                    doctor.DoctorError, "symlink or reparse-point"
                ):
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(outside_reads, [])
            self.assertEqual(outside_target.read_bytes(), b"outside-original")
            self.assertFalse(hook_path.exists())

    @unittest.skipIf(os.name == "nt", "Unix symlink regression")
    def test_unix_hook_symlink_is_rejected_without_outside_read_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            hook_path.parent.mkdir(parents=True)
            outside_hook = root / "outside-hook.py"
            outside_hook.write_bytes(b"outside-original")
            hook_path.symlink_to(outside_hook)
            outside_reads: list[Path] = []
            original_read_bytes = Path.read_bytes

            def track_read(path: Path) -> bytes:
                if path.resolve(strict=False) == outside_hook.resolve():
                    outside_reads.append(path)
                return original_read_bytes(path)

            with mock.patch.object(Path, "read_bytes", track_read):
                with self.assertRaisesRegex(
                    doctor.DoctorError, "symlink or reparse-point"
                ):
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(outside_reads, [])
            self.assertEqual(outside_hook.read_bytes(), b"outside-original")

    @unittest.skipUnless(os.name == "nt", "manual repair requires handle-bound replace")
    def test_safe_nested_skill_directories_remain_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hooks" / "hook.py"

            report = _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(report["status"], "updated")
            self.assertTrue((skill_root / "references" / "operations.md").is_file())
            self.assertTrue((skill_root / "scripts" / "coordination_state.py").is_file())

    def test_missing_safe_platform_primitive_requires_manual_action_before_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "installed" / "skill" / "SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"must-not-be-read")
            unavailable = (
                mock.patch.object(
                    doctor.ctypes,
                    "WinDLL",
                    side_effect=OSError("simulated missing Windows handle API"),
                )
                if os.name == "nt"
                else mock.patch.object(doctor.os, "supports_dir_fd", set())
            )
            with unavailable, mock.patch.object(Path, "read_bytes") as read_bytes:
                with self.assertRaisesRegex(
                    doctor.DoctorError,
                    "manual action is required before installed-target content access",
                ):
                    doctor._InstalledTargetAccess(
                        target.parent, root / "installed" / "hook.py"
                    )
            read_bytes.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows handle-race regression")
    def test_windows_held_parent_detects_read_component_swap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "installed" / "skill"
            scripts = skill_root / "scripts"
            scripts.mkdir(parents=True)
            target = scripts / "coordination_state.py"
            target.write_bytes(b"installed-local")
            hook_path = root / "installed" / "hook.py"
            hook_path.write_bytes(b"hook-local")
            outside = root / "outside"
            outside.mkdir()
            (outside / target.name).write_bytes(b"outside-secret")
            access = doctor._InstalledTargetAccess(skill_root, hook_path)
            original_open = access._windows_open_relative
            blocked_swaps: set[str] = set()

            def attempt_swap(
                parent: int,
                name: str,
                **kwargs: object,
            ) -> int:
                handle = original_open(parent, name, **kwargs)
                if name == target.name and not kwargs.get("directory"):
                    try:
                        scripts.rename(skill_root / "saved-scripts")
                    except PermissionError:
                        blocked_swaps.add("parent")
                    try:
                        target.rename(scripts / "saved-state.py")
                    except PermissionError:
                        blocked_swaps.add("file")
                return handle

            with mock.patch.object(access, "_windows_open_relative", side_effect=attempt_swap):
                with self.assertRaisesRegex(
                    doctor.DoctorError, "does not match its authorised path"
                ):
                    access.read_bytes(target)

            self.assertEqual(blocked_swaps, {"parent"})
            self.assertEqual((outside / target.name).read_bytes(), b"outside-secret")

    @unittest.skipUnless(os.name == "nt", "Windows handle-race regression")
    def test_windows_held_parent_blocks_write_replace_and_cleanup_swaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "installed" / "skill"
            scripts = skill_root / "scripts"
            scripts.mkdir(parents=True)
            target = scripts / "coordination_state.py"
            target.write_bytes(b"last-good")
            hook_path = root / "installed" / "hook.py"
            hook_path.write_bytes(b"hook-local")
            outside = root / "outside"
            outside.mkdir()
            outside_target = outside / target.name
            outside_target.write_bytes(b"outside-original")
            access = doctor._InstalledTargetAccess(skill_root, hook_path)
            original_write = access._windows_write_handle
            blocked_attempts = 0

            def attempt_swap_then_write(handle: int, data: bytes) -> None:
                nonlocal blocked_attempts
                try:
                    scripts.rename(skill_root / "saved-scripts")
                except PermissionError:
                    blocked_attempts += 1
                original_write(handle, data)

            with mock.patch.object(
                access, "_windows_write_handle", side_effect=attempt_swap_then_write
            ):
                access.atomic_write(target, b"updated-local")

            self.assertGreaterEqual(blocked_attempts, 1)
            self.assertEqual(target.read_bytes(), b"updated-local")
            self.assertEqual(outside_target.read_bytes(), b"outside-original")
            self.assertEqual(list(scripts.glob(".*.tmp")), [])

            def attempt_swap_then_fail(handle: int, data: bytes) -> None:
                nonlocal blocked_attempts
                try:
                    scripts.rename(skill_root / "saved-scripts")
                except PermissionError:
                    blocked_attempts += 1
                raise OSError("simulated temporary-write failure")

            with mock.patch.object(
                access, "_windows_write_handle", side_effect=attempt_swap_then_fail
            ):
                with self.assertRaisesRegex(OSError, "temporary-write failure"):
                    access.atomic_write(target, b"rollback-bytes")

            self.assertEqual(target.read_bytes(), b"updated-local")
            self.assertEqual(outside_target.read_bytes(), b"outside-original")
            self.assertEqual(list(scripts.glob(".*.tmp")), [])

    @unittest.skipUnless(os.name != "nt", "Unix descriptor-race regression")
    def test_unix_read_stays_on_held_parent_but_apply_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "installed" / "skill"
            scripts = skill_root / "scripts"
            scripts.mkdir(parents=True)
            target = scripts / "coordination_state.py"
            target.write_bytes(b"installed-local")
            hook_path = root / "installed" / "hook.py"
            hook_path.write_bytes(b"hook-local")
            outside = root / "outside"
            outside.mkdir()
            outside_target = outside / target.name
            outside_target.write_bytes(b"outside-secret")
            access = doctor._InstalledTargetAccess(skill_root, hook_path)
            original_open = os.open
            redirected = False

            def swap_before_file_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
                nonlocal redirected
                if path == target.name and kwargs.get("dir_fd") is not None and not redirected:
                    scripts.rename(skill_root / "saved-scripts")
                    scripts.symlink_to(outside, target_is_directory=True)
                    redirected = True
                return original_open(path, flags, *args, **kwargs)

            with mock.patch.object(os, "open", side_effect=swap_before_file_open):
                self.assertEqual(access.read_bytes(target), b"installed-local")

            self.assertTrue(redirected)
            self.assertEqual(outside_target.read_bytes(), b"outside-secret")

            scripts.unlink()
            saved_scripts = skill_root / "saved-scripts"
            saved_scripts.rename(scripts)
            with mock.patch.object(os, "open") as open_file, mock.patch.object(
                os, "rename"
            ) as rename:
                with self.assertRaisesRegex(
                    doctor.DoctorError,
                    "no handle-bound atomic replacement primitive",
                ):
                    access.atomic_write(target, b"updated-local")

            open_file.assert_not_called()
            rename.assert_not_called()
            self.assertEqual(target.read_bytes(), b"installed-local")
            self.assertEqual(outside_target.read_bytes(), b"outside-secret")
            self.assertEqual(list(scripts.glob(".*.tmp")), [])

    @unittest.skipUnless(os.name != "nt", "Unix handle-bound replace regression")
    def test_unix_manual_apply_reports_manual_action_before_target_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            identity = _release_identity(source)

            with mock.patch("builtins.print") as output:
                result = doctor.main(
                    [
                        "--source-plugin",
                        str(source),
                        "--skill-root",
                        str(skill_root),
                        "--hook-path",
                        str(hook_path),
                        "--installation-kind",
                        "manual",
                        "--expected-package-version",
                        identity["expected_package_version"],
                        "--expected-receipt-sha256",
                        identity["expected_receipt_sha256"],
                        "--apply",
                        "--compact",
                    ]
                )

            payload = json.loads(output.call_args.args[0])
            self.assertEqual(result, 1)
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["recoveryState"], "manual_action_required")
            self.assertIn("no handle-bound atomic replacement primitive", payload["error"])
            self.assertFalse(skill_root.exists())
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

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
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
            original_write = doctor._InstalledTargetAccess.atomic_write
            writes = 0

            def fail_second_write(
                access: object, path: Path, data: bytes
            ) -> None:
                nonlocal writes
                writes += 1
                if writes == 2:
                    raise OSError("simulated later write failure")
                original_write(access, path, data)

            with mock.patch.object(
                doctor._InstalledTargetAccess, "atomic_write", new=fail_second_write
            ):
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

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
    def test_runtime_error_after_first_replacement_restores_last_good_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            last_good = b"print('last good hook')\n"
            hook_path.write_bytes(last_good)
            original_write = doctor._InstalledTargetAccess.atomic_write
            replaced = False

            def fail_after_first_replace(
                access: object, path: Path, data: bytes
            ) -> None:
                nonlocal replaced
                original_write(access, path, data)
                if Path(path) == hook_path and not replaced:
                    replaced = True
                    raise RuntimeError("simulated post-replace runtime failure")

            with mock.patch.object(
                doctor._InstalledTargetAccess,
                "atomic_write",
                new=fail_after_first_replace,
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            report = failure.exception.report
            self.assertTrue(replaced)
            self.assertEqual(report["status"], "error")
            self.assertEqual(report["recoveryState"], "repair_failed_last_good_restored")
            self.assertTrue(report["rollback"]["attempted"])
            self.assertTrue(report["rollback"]["lastGoodRestored"])
            self.assertEqual(report["rollback"]["errors"], [])
            self.assertIn("post-replace runtime failure", report["error"])
            self.assertEqual(hook_path.read_bytes(), last_good)

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
    def test_ordinary_rollback_and_cleanup_errors_are_complete_and_truthful(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            skill_path = skill_root / "SKILL.md"
            missing_path = skill_root / doctor.CAPABILITY_CONTRACT
            hook_last_good = b"print('last good hook')\n"
            skill_last_good = b"# Last good skill\n"
            hook_path.write_bytes(hook_last_good)
            skill_path.write_bytes(skill_last_good)
            missing_path.unlink()
            source_skill = (source / "skills" / "codex-coordinator" / "SKILL.md").read_bytes()
            original_write = doctor._InstalledTargetAccess.atomic_write
            original_unlink = doctor._InstalledTargetAccess.unlink
            transaction_failed = False
            rollback_attempts: list[Path] = []

            def fail_transaction_and_one_restore(
                access: object, path: Path, data: bytes
            ) -> None:
                nonlocal transaction_failed
                target = Path(path)
                if transaction_failed:
                    rollback_attempts.append(target)
                    if target == skill_path:
                        raise RuntimeError("simulated rollback runtime failure")
                    original_write(access, path, data)
                    return
                original_write(access, path, data)
                if target == missing_path:
                    transaction_failed = True
                    raise RuntimeError("simulated transaction runtime failure")

            def fail_after_cleanup(
                access: object, path: Path, *, missing_ok: bool = False
            ) -> None:
                rollback_attempts.append(Path(path))
                original_unlink(access, path, missing_ok=missing_ok)
                raise RuntimeError("simulated rollback cleanup failure")

            with mock.patch.object(
                doctor._InstalledTargetAccess,
                "atomic_write",
                new=fail_transaction_and_one_restore,
            ), mock.patch.object(
                doctor._InstalledTargetAccess,
                "unlink",
                new=fail_after_cleanup,
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            report = failure.exception.report
            self.assertTrue(transaction_failed)
            self.assertEqual(
                rollback_attempts,
                [missing_path, skill_path, hook_path],
            )
            self.assertEqual(report["status"], "error")
            self.assertEqual(report["recoveryState"], "manual_action_required")
            self.assertTrue(report["rollback"]["attempted"])
            self.assertFalse(report["rollback"]["lastGoodRestored"])
            self.assertEqual(len(report["rollback"]["errors"]), 2)
            self.assertIn(
                f"{doctor.CAPABILITY_CONTRACT} -> {missing_path}: simulated rollback cleanup failure",
                report["rollback"]["errors"],
            )
            self.assertIn(
                f"SKILL.md -> {skill_path}: simulated rollback runtime failure",
                report["rollback"]["errors"],
            )
            self.assertIn("transaction runtime failure", report["error"])
            self.assertEqual(hook_path.read_bytes(), hook_last_good)
            self.assertEqual(skill_path.read_bytes(), source_skill)
            self.assertFalse(missing_path.exists())

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
    def test_unproven_native_temp_cleanup_requires_manual_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            skill_path = skill_root / "SKILL.md"
            last_good = b"# Locally modified last-good skill\n"
            skill_path.write_bytes(last_good)
            original_atomic_write = doctor._InstalledTargetAccess._windows_atomic_write
            failed_once = False

            def fail_first_temp_write_and_cleanup(
                access: object, path: Path, data: bytes
            ) -> None:
                nonlocal failed_once
                if failed_once:
                    original_atomic_write(access, path, data)
                    return
                failed_once = True
                with mock.patch.object(
                    access,
                    "_windows_write_handle",
                    side_effect=RuntimeError("simulated first temporary write failure"),
                ), mock.patch.object(
                    access._kernel32,
                    "SetFileInformationByHandle",
                    return_value=0,
                ):
                    original_atomic_write(access, path, data)

            with mock.patch.object(
                doctor._InstalledTargetAccess,
                "_windows_atomic_write",
                new=fail_first_temp_write_and_cleanup,
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            residuals = list(skill_path.parent.glob(f".{skill_path.name}.*.tmp"))
            report = failure.exception.report
            self.assertTrue(failed_once)
            self.assertEqual(report["recoveryState"], "manual_action_required")
            self.assertFalse(report["rollback"]["lastGoodRestored"])
            self.assertEqual(len(report["rollback"]["errors"]), 1)
            self.assertEqual(len(residuals), 1)
            self.assertIn(str(residuals[0]), report["rollback"]["errors"][0])
            self.assertIn(
                "SetFileInformationByHandle returned 0",
                report["rollback"]["errors"][0],
            )
            self.assertIn("simulated first temporary write failure", report["error"])
            self.assertEqual(skill_path.read_bytes(), last_good)

    @unittest.skipUnless(os.name == "nt", "Windows checked-handle cleanup regression")
    def test_parent_traversal_read_and_final_parent_close_failures_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "installed" / "skill"
            target = skill_root / "nested" / "file.txt"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"installed")
            hook_path = root / "installed" / "hook.py"
            hook_path.write_bytes(b"hook")

            cases = (
                ("parent traversal", Path(target.anchor), 2),
                ("read", target, 1),
                ("final parent", target.parent, 1),
            )
            for label, selected_target, expected_errors in cases:
                with self.subTest(lifetime=label):
                    access = doctor._InstalledTargetAccess(skill_root, hook_path)
                    original_close = access._windows_close_error
                    failed = False

                    def fail_selected_close(handle: int, close_target: Path) -> str | None:
                        nonlocal failed
                        error = original_close(handle, close_target)
                        if Path(close_target) == selected_target and not failed:
                            failed = True
                            return (
                                f"native handle cleanup unproven for {close_target}: "
                                f"CloseHandle returned 0 (Windows error 6: simulated {label})"
                            )
                        return error

                    with mock.patch.object(
                        access, "_windows_close_error", side_effect=fail_selected_close
                    ):
                        with self.assertRaises(doctor._InstalledMutationError) as failure:
                            access.read_bytes(target)

                    self.assertIn(label, str(failure.exception))
                    self.assertTrue(failed)
                    self.assertEqual(
                        len(failure.exception.recovery_errors), expected_errors
                    )

    @unittest.skipUnless(os.name == "nt", "Windows checked-handle cleanup regression")
    def test_rejected_child_and_unlink_close_failures_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "installed" / "skill"
            rejected = skill_root / "rejected"
            rejected.mkdir(parents=True)
            target = rejected / "file.txt"
            target.write_bytes(b"installed")
            hook_path = root / "installed" / "hook.py"
            hook_path.write_bytes(b"hook")

            access = doctor._InstalledTargetAccess(skill_root, hook_path)
            original_validate = access._windows_validate_handle
            original_close = access._windows_close_error

            def reject_child(
                handle: int, expected: Path, *, directory: bool
            ) -> None:
                if directory and Path(expected) == rejected:
                    raise doctor.DoctorError("simulated rejected child")
                original_validate(handle, expected, directory=directory)

            def fail_rejected_close(handle: int, close_target: Path) -> str | None:
                error = original_close(handle, close_target)
                if Path(close_target) == rejected:
                    return (
                        f"native handle cleanup unproven for {rejected}: "
                        "CloseHandle returned 0 (Windows error 6: simulated rejected child)"
                    )
                return error

            with mock.patch.object(
                access, "_windows_validate_handle", side_effect=reject_child
            ), mock.patch.object(
                access, "_windows_close_error", side_effect=fail_rejected_close
            ):
                with self.assertRaises(doctor._InstalledMutationError) as rejected_failure:
                    access.read_bytes(target)

            self.assertIn(str(rejected), rejected_failure.exception.recovery_errors[0])

            access = doctor._InstalledTargetAccess(skill_root, hook_path)
            original_close = access._windows_close_error

            def fail_unlink_close(handle: int, close_target: Path) -> str | None:
                error = original_close(handle, close_target)
                if Path(close_target) == target:
                    return (
                        f"native handle cleanup unproven for {target}: "
                        "CloseHandle returned 0 (Windows error 6: simulated unlink)"
                    )
                return error

            with mock.patch.object(
                access, "_windows_close_error", side_effect=fail_unlink_close
            ):
                with self.assertRaises(doctor._InstalledMutationError) as unlink_failure:
                    access.unlink(target, missing_ok=False)

            self.assertIn(str(target), unlink_failure.exception.recovery_errors[0])

    @unittest.skipUnless(os.name == "nt", "Windows BaseException cleanup regression")
    def test_close_failure_never_masks_base_exception(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "installed" / "skill"
            target = skill_root / "file.txt"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"installed")
            hook_path = root / "installed" / "hook.py"
            hook_path.write_bytes(b"hook")
            access = doctor._InstalledTargetAccess(skill_root, hook_path)
            original_close = access._windows_close_error

            def fail_file_close(handle: int, close_target: Path) -> str | None:
                error = original_close(handle, close_target)
                if Path(close_target) == target:
                    return (
                        f"native handle cleanup unproven for {target}: "
                        "CloseHandle returned 0 (Windows error 6: simulated cleanup failure)"
                    )
                return error

            with mock.patch.object(
                access, "_windows_read_handle", side_effect=KeyboardInterrupt
            ), mock.patch.object(
                access, "_windows_close_error", side_effect=fail_file_close
            ):
                with self.assertRaises(KeyboardInterrupt):
                    access.read_bytes(target)

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
    def test_absence_rollback_close_failure_never_claims_restoration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            missing_path = skill_root / doctor.CAPABILITY_CONTRACT
            missing_path.unlink()
            original_close = doctor._InstalledTargetAccess._windows_close_error
            original_unlink = doctor._InstalledTargetAccess._windows_unlink
            rolling_back_absence = False
            close_failed = False

            def fail_absence_rollback_close(
                access: object, handle: int, close_target: Path
            ) -> str | None:
                nonlocal close_failed
                error = original_close(access, handle, close_target)
                if rolling_back_absence and Path(close_target).name == missing_path.name:
                    close_failed = True
                    return (
                        f"native handle cleanup unproven for {missing_path}: "
                        "CloseHandle returned 0 (Windows error 6: simulated absence rollback)"
                    )
                return error

            def mark_absence_rollback(
                access: object, path: Path, *, missing_ok: bool
            ) -> None:
                nonlocal rolling_back_absence
                rolling_back_absence = True
                try:
                    original_unlink(access, path, missing_ok=missing_ok)
                finally:
                    rolling_back_absence = False

            with mock.patch.object(
                doctor._InstalledTargetAccess,
                "_windows_close_error",
                new=fail_absence_rollback_close,
            ), mock.patch.object(
                doctor._InstalledTargetAccess,
                "_windows_unlink",
                new=mark_absence_rollback,
            ), mock.patch.object(
                doctor,
                "_validate_installation",
                side_effect=RuntimeError("force rollback after missing-file replacement"),
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            report = failure.exception.report
            self.assertTrue(close_failed)
            self.assertEqual(report["recoveryState"], "manual_action_required")
            self.assertFalse(report["rollback"]["lastGoodRestored"])
            self.assertIn(str(missing_path), report["rollback"]["errors"][0])

    @unittest.skipUnless(os.name == "nt", "Windows leaked-handle sharing regression")
    def test_leaked_target_handle_sharing_error_is_reported_as_unrestored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            skill_path = skill_root / "SKILL.md"
            last_good = b"# Last good before leaked handle\n"
            skill_path.write_bytes(last_good)
            original_close = doctor._InstalledTargetAccess._windows_close_error
            leaked_handle: int | None = None
            target_closes = 0

            def leak_first_replaced_target(
                access: object, handle: int, close_target: Path
            ) -> str | None:
                nonlocal leaked_handle, target_closes
                if Path(close_target) == skill_path:
                    target_closes += 1
                    if target_closes == 2 and leaked_handle is None:
                        leaked_handle = handle
                        return (
                            f"native handle cleanup unproven for {skill_path}: "
                            "CloseHandle returned 0 (Windows error 6: simulated leaked handle)"
                        )
                return original_close(access, handle, close_target)

            try:
                with mock.patch.object(
                    doctor._InstalledTargetAccess,
                    "_windows_close_error",
                    new=leak_first_replaced_target,
                ):
                    with self.assertRaises(doctor.RepairFailed) as failure:
                        _sync_installation(source, skill_root, hook_path, apply=True)
            finally:
                if leaked_handle is not None:
                    doctor.ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(
                        leaked_handle
                    )

            report = failure.exception.report
            self.assertIsNotNone(leaked_handle)
            self.assertEqual(report["recoveryState"], "manual_action_required")
            self.assertFalse(report["rollback"]["lastGoodRestored"])
            self.assertTrue(any(str(skill_path) in error for error in report["rollback"]["errors"]))
            self.assertTrue(
                any(
                    "used by another process" in error.lower()
                    or "sharing" in error.lower()
                    or "windows error 32" in error.lower()
                    or "access is denied" in error.lower()
                    for error in report["rollback"]["errors"]
                ),
                report["rollback"]["errors"],
            )

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
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
            original_write = doctor._InstalledTargetAccess.atomic_write
            writes = 0

            def fail_update_and_restore(
                access: object, path: Path, data: bytes
            ) -> None:
                nonlocal writes
                writes += 1
                if writes in {2, 3}:
                    raise OSError("simulated update or restore failure")
                original_write(access, path, data)

            with mock.patch.object(
                doctor._InstalledTargetAccess,
                "atomic_write",
                new=fail_update_and_restore,
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(
                failure.exception.report["recoveryState"], "manual_action_required"
            )
            self.assertFalse(failure.exception.report["rollback"]["lastGoodRestored"])
            self.assertEqual(len(failure.exception.report["rollback"]["errors"]), 1)

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
    def test_rollback_rejects_new_directory_redirect_without_outside_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            state_tool = skill_root / "scripts" / "coordination_state.py"
            state_tool.write_bytes(b"last-good-local")
            outside = root / "outside"
            outside.mkdir()
            outside_target = outside / "coordination_state.py"
            outside_target.write_bytes(b"outside-original")
            saved_scripts = skill_root / "saved-scripts"

            def redirect_before_validation(*args: object, **kwargs: object) -> object:
                (skill_root / "scripts").rename(saved_scripts)
                _redirect_directory(skill_root / "scripts", outside)
                raise doctor.DoctorError("simulated validation failure after redirect")

            outside_reads: list[Path] = []
            original_read_bytes = Path.read_bytes

            def track_read(path: Path) -> bytes:
                try:
                    path.resolve(strict=False).relative_to(outside.resolve())
                except ValueError:
                    pass
                else:
                    outside_reads.append(path)
                return original_read_bytes(path)

            with mock.patch.object(
                doctor, "_validate_installation", side_effect=redirect_before_validation
            ), mock.patch.object(Path, "read_bytes", track_read):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(
                failure.exception.report["recoveryState"], "manual_action_required"
            )
            self.assertFalse(failure.exception.report["rollback"]["lastGoodRestored"])
            self.assertIn(
                "symlink or reparse-point",
                failure.exception.report["rollback"]["errors"][0],
            )
            self.assertEqual(outside_reads, [])
            self.assertEqual(outside_target.read_bytes(), b"outside-original")
            self.assertEqual(
                (saved_scripts / "coordination_state.py").read_bytes(),
                (source / "skills" / "codex-coordinator" / "scripts" / "coordination_state.py").read_bytes(),
            )

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
    def test_post_replace_directory_swap_restores_last_good_at_safe_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            scripts = skill_root / "scripts"
            state_tool = scripts / "coordination_state.py"
            state_tool.write_bytes(b"last-good-local")
            outside = root / "outside"
            outside.mkdir()
            outside_target = outside / "coordination_state.py"
            outside_target.write_bytes(b"outside-original")
            saved_scripts = skill_root / "saved-scripts"
            original_write = doctor._InstalledTargetAccess.atomic_write
            redirected = False

            def swap_after_replace(access: object, path: Path, data: bytes) -> None:
                nonlocal redirected
                original_write(access, path, data)
                if Path(path) == state_tool and not redirected:
                    scripts.rename(saved_scripts)
                    _redirect_directory(scripts, outside)
                    _remove_redirect_directory(scripts)
                    saved_scripts.rename(scripts)
                    redirected = True
                    raise OSError("simulated post-replace directory swap")

            with mock.patch.object(
                doctor._InstalledTargetAccess,
                "atomic_write",
                new=swap_after_replace,
            ):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertTrue(redirected)
            self.assertEqual(
                failure.exception.report["recoveryState"],
                "repair_failed_last_good_restored",
            )
            self.assertTrue(failure.exception.report["rollback"]["lastGoodRestored"])
            self.assertEqual(
                failure.exception.report["rollback"]["errors"], []
            )
            self.assertEqual(state_tool.read_bytes(), b"last-good-local")
            self.assertEqual(outside_target.read_bytes(), b"outside-original")

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
    def test_post_replace_directory_swap_never_claims_unproven_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root / "source")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            _sync_installation(source, skill_root, hook_path, apply=True)
            scripts = skill_root / "scripts"
            state_tool = scripts / "coordination_state.py"
            state_tool.write_bytes(b"last-good-local")
            outside = root / "outside"
            outside.mkdir()
            outside_target = outside / "coordination_state.py"
            outside_target.write_bytes(b"outside-original")
            saved_scripts = skill_root / "saved-scripts"
            original_write = doctor._InstalledTargetAccess.atomic_write
            original_read_bytes = Path.read_bytes
            outside_reads: list[Path] = []
            redirected = False

            def redirect_after_replace(access: object, path: Path, data: bytes) -> None:
                nonlocal redirected
                original_write(access, path, data)
                if Path(path) == state_tool and not redirected:
                    scripts.rename(saved_scripts)
                    _redirect_directory(scripts, outside)
                    redirected = True

            def track_read(path: Path) -> bytes:
                try:
                    path.resolve(strict=False).relative_to(outside.resolve())
                except ValueError:
                    pass
                else:
                    outside_reads.append(path)
                return original_read_bytes(path)

            with mock.patch.object(
                doctor._InstalledTargetAccess,
                "atomic_write",
                new=redirect_after_replace,
            ), mock.patch.object(Path, "read_bytes", track_read):
                with self.assertRaises(doctor.RepairFailed) as failure:
                    _sync_installation(source, skill_root, hook_path, apply=True)

            self.assertTrue(redirected)
            self.assertEqual(
                failure.exception.report["recoveryState"], "manual_action_required"
            )
            self.assertFalse(failure.exception.report["rollback"]["lastGoodRestored"])
            self.assertEqual(len(failure.exception.report["rollback"]["errors"]), 1)
            self.assertIn(str(state_tool), failure.exception.report["rollback"]["errors"][0])
            self.assertIn(
                "symlink or reparse-point",
                failure.exception.report["rollback"]["errors"][0],
            )
            self.assertEqual(outside_reads, [])
            self.assertEqual(
                original_read_bytes(outside_target), b"outside-original"
            )
            self.assertNotEqual(
                original_read_bytes(saved_scripts / "coordination_state.py"),
                b"last-good-local",
            )

    @unittest.skipUnless(os.name == "nt", "manual rollback requires handle-bound replace")
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
