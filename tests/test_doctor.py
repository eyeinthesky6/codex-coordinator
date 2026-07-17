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

[Operations](references/operations.md)

Coordinator is control-first by default.
Use one temporary native heartbeat.
For every generated task, set reasoning explicitly to `low` or `medium`.
Subagents remain available as parent-owned helpers.
Use scripts/coordination_state.py.
"""

OPERATIONS_TEXT = """# Source operations

Put the complete executable assignment in the native creation prompt.
Subagents remain available inside a registered task.
Use codex_app__automation_update, codex_app__set_thread_pinned,
codex_app__set_thread_archived, codex_app__fork_thread, and
codex_app__handoff_thread.
Inherit the user's configured model, but use cost-safe reasoning.
Pass native thinking or the host's equivalent reasoning field as low or medium.
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
            self.assertEqual(check["changedFiles"], 5)

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

    def test_stale_operating_guidance_is_rejected_even_when_contract_claims_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = _source_plugin(root)
            operations = source / "skills" / "codex-coordinator" / "references" / "operations.md"
            operations.write_text(
                OPERATIONS_TEXT.replace(
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
