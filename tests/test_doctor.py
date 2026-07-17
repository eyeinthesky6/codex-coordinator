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
Use one temporary native heartbeat.
For every generated task, set reasoning explicitly to `low` or `medium`.
Subagents remain available as parent-owned helpers.
Apply the durable-thread gate before creating a user-visible worker.
Task registration, acceptance, ownership recording, and permission-to-continue confirmations are document-only.
Use scripts/coordination_state.py.
Use the two-phase inbox hash checkpoint.
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
"""

RECONCILIATION_TEXT = """# Source reconciliation

Use scan-inbox and ack-inbox as a two-phase checkpoint.
Use afterCursor when native tasks expose it. Do not persist or mirror native turns.
Use codex_app__automation_update, codex_app__set_thread_pinned,
codex_app__set_thread_archived, codex_app__fork_thread, and
codex_app__handoff_thread.
Never send task registration, acceptance, task-ID assignment, ownership confirmation, or permission-to-continue messages.
"""

MESSAGING_TEXT = """# Source messaging

Project-bound routing uses the Native task messenger.
Never switch to the collaboration messenger as a fallback.
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
            self.assertEqual(check["changedFiles"], 8)

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

if __name__ == "__main__":
    unittest.main()
