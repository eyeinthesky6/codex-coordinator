from __future__ import annotations

import importlib.util
import json
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
        json.dumps({"name": name, "version": "1.0.0"}), encoding="utf-8"
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
    return plugin


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

            with mock.patch("builtins.print") as print_output:
                result = doctor.main(
                    [
                        "--source-plugin",
                        str(source),
                        "--skill-root",
                        str(skill_root),
                        "--hook-path",
                        str(hook_path),
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

            with mock.patch("builtins.print") as print_output:
                result = doctor.main(
                    [
                        "--source-plugin",
                        str(source),
                        "--skill-root",
                        str(skill_root),
                        "--hook-path",
                        str(hook_path),
                        "--compact",
                        "--check",
                    ]
                )

            self.assertEqual(result, 2)
            raw = print_output.call_args.args[0]
            self.assertLess(len(raw.encode("utf-8")), 200)
            payload = json.loads(raw)
            self.assertEqual(set(payload), {"status", "changedFiles", "checksPassed"})
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

            check = doctor.sync_installation(source, skill_root, hook_path, apply=False)
            self.assertEqual(check["status"], "drift")
            self.assertEqual(check["changedFiles"], 12)

            applied = doctor.sync_installation(source, skill_root, hook_path, apply=True)
            self.assertEqual(applied["status"], "updated")
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

            current = doctor.sync_installation(source, skill_root, hook_path, apply=False)
            self.assertEqual(current["status"], "current")
            self.assertEqual(current["changedFiles"], 0)

    def test_wrong_plugin_source_is_rejected_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root, name="another-plugin")
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"

            with self.assertRaises(doctor.DoctorError):
                doctor.sync_installation(source, skill_root, hook_path, apply=True)
            self.assertFalse(skill_root.exists())
            self.assertFalse(hook_path.exists())

    def test_hook_destination_cannot_overlap_the_installed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            skill_root = root / "installed" / "skill"
            hook_path = skill_root / "scripts" / "coordination_state.py"

            with self.assertRaisesRegex(doctor.DoctorError, "overlap"):
                doctor.sync_installation(source, skill_root, hook_path, apply=True)
            self.assertFalse(skill_root.exists())

    def test_installed_skill_cannot_be_nested_under_hook_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            hook_path = root / "installed" / "hook.py"
            skill_root = hook_path / "skill"

            with self.assertRaisesRegex(doctor.DoctorError, "overlap"):
                doctor.sync_installation(source, skill_root, hook_path, apply=True)
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
                doctor.sync_installation(
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
                doctor.sync_installation(
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
                with self.assertRaisesRegex(doctor.DoctorError, "rolled back"):
                    doctor.sync_installation(source, skill_root, hook_path, apply=True)

            self.assertEqual(
                (skill_root / "SKILL.md").read_text(encoding="utf-8"), "# Old skill\n"
            )
            self.assertEqual(
                (skill_root / "references" / "operations.md").read_text(encoding="utf-8"),
                "# Old operations\n",
            )
            self.assertEqual(hook_path.read_text(encoding="utf-8"), "print('old hook')\n")

    def test_installed_runtime_failure_rolls_back_the_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            (source / "scripts" / doctor.HOOK_NAME).write_text(
                "raise SystemExit(7)\n", encoding="utf-8"
            )
            skill_root = root / "installed" / "skill"
            hook_path = root / "installed" / "hook.py"
            (skill_root / "references").mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("# Old skill\n", encoding="utf-8")
            (skill_root / "references" / "operations.md").write_text(
                "# Old operations\n", encoding="utf-8"
            )
            hook_path.write_text("print('old hook')\n", encoding="utf-8")

            with self.assertRaisesRegex(doctor.DoctorError, "smoke check failed"):
                doctor.sync_installation(source, skill_root, hook_path, apply=True)

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
                doctor.sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=True,
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
                doctor.sync_installation(
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
                doctor.sync_installation(
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
                doctor.sync_installation(
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
                doctor.sync_installation(
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
                doctor.sync_installation(
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
                doctor.sync_installation(
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
                doctor.sync_installation(
                    source,
                    root / "installed" / "skill",
                    root / "installed" / "hook.py",
                    apply=False,
                )

if __name__ == "__main__":
    unittest.main()
