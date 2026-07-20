from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
HOOK = PLUGIN / "scripts" / "codex_coordinator_session_start.py"
COORDINATOR_ID = "11111111-1111-4111-8111-111111111111"
WORKER_ID = "22222222-2222-4222-8222-222222222222"


def _load_hook_module():
    module_name = "codex_coordinator_session_start_test_module"
    spec = importlib.util.spec_from_file_location(module_name, HOOK)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load hook module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["CODEX_COORDINATOR_DISABLE_MISSION_CONTROL_AUTOSTART"] = "1"
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )


def _table(headers: list[str], rows: list[dict[str, str]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(row[header] for header in headers) + " |" for row in rows)
    return "\n".join(output)


def _marker(
    project_id: str = "sample-project",
    *,
    schema_version: str = "1",
    task_access: str = "false",
    state_changes: str = "false",
) -> str:
    return f"""schema_version: {schema_version}
coordination_enabled: true
project_id: {project_id}
project_name: Sample Project
task_prefix: SAMPLE
canonical_paths:
  current: .codex/coordination/CURRENT.md
  tasks: .codex/coordination/tasks
  suggestions: .codex/coordination/suggestions
access:
  cross_project_task_access: {task_access}
  cross_project_state_changes: {state_changes}
"""


def _current(
    *,
    project_id: str = "sample-project",
    coordinator_task: str = "SAMPLE-001",
    coordinator_status: str = "ACTIVE",
    coordinator_accepts: str = "true",
    coordinator_row_status: str | None = None,
    coordinator_row_accepts: str | None = None,
    worker_task: str = "SAMPLE-002",
    worker_status: str = "ACTIVE",
    worker_accepts: str = "true",
    include_worker: bool = True,
    include_active_coordinator: bool = True,
    include_active_worker: bool = True,
    reorder: bool = False,
    shared_goal: str | None = None,
    last_reconciliation: str = "2026-07-15T12:00:00Z",
) -> str:
    registered_headers = [
        "Thread ID",
        "Thread name",
        "Scope kind",
        "Role",
        "Task ID",
        "Status",
        "Accepts project messages",
    ]
    active_headers = ["Task ID", "Owner", "Role", "Status"]
    pending_headers = [
        "Task ID",
        "Message ID",
        "Recipient thread ID",
        "Message type",
        "Status",
    ]
    resume_headers = ["Task ID", "Message ID", "Resume condition", "Status"]
    paused_headers = ["Task ID", "Owner", "Reason", "Resume condition", "Status"]
    blocked_headers = ["Decision ID", "Task ID", "Decision needed", "Status"]
    if reorder:
        registered_headers = [
            "Status",
            "Task ID",
            "Thread name",
            "Accepts project messages",
            "Role",
            "Thread ID",
            "Scope kind",
        ]
        active_headers = ["Status", "Role", "Owner", "Task ID"]
        pending_headers = [
            "Message type",
            "Status",
            "Recipient thread ID",
            "Task ID",
            "Message ID",
        ]
        resume_headers = ["Resume condition", "Status", "Message ID", "Task ID"]
        paused_headers = ["Status", "Resume condition", "Reason", "Owner", "Task ID"]
        blocked_headers = ["Status", "Decision needed", "Task ID", "Decision ID"]

    sessions = [
        {
            "Thread ID": COORDINATOR_ID,
            "Thread name": "Project Coordinator",
            "Scope kind": "PROJECT_EXECUTION",
            "Role": "COORDINATOR",
            "Task ID": coordinator_task,
            "Status": coordinator_row_status or coordinator_status,
            "Accepts project messages": coordinator_row_accepts or coordinator_accepts,
        }
    ]
    if include_worker:
        sessions.append(
            {
                "Thread ID": WORKER_ID,
                "Thread name": "Hook Worker",
                "Scope kind": "PROJECT_EXECUTION",
                "Role": "TASK_AGENT",
                "Task ID": worker_task,
                "Status": worker_status,
                "Accepts project messages": worker_accepts,
            }
        )

    active: list[dict[str, str]] = []
    if include_active_coordinator:
        active.append(
            {
                "Task ID": "SAMPLE-001",
                "Owner": COORDINATOR_ID,
                "Role": "COORDINATOR",
                "Status": "ACTIVE",
            }
        )
    if include_active_worker:
        active.append(
            {
                "Task ID": "SAMPLE-002",
                "Owner": WORKER_ID,
                "Role": "TASK_AGENT",
                "Status": "ACTIVE",
            }
        )

    pending = []
    if include_worker:
        pending.append(
            {
                "Task ID": "SAMPLE-002",
                "Message ID": "MSG-001",
                "Recipient thread ID": WORKER_ID,
                "Message type": "AMEND_TASK",
                "Status": "PENDING",
            }
        )

    mode = "MANAGING"
    resolved_shared_goal = (
        shared_goal
        if shared_goal is not None
        else ("none" if coordinator_task == "NONE" and not active else "test hook behavior")
    )
    return f"""# Codex Coordinator state

**Project ID:** `{project_id}`
**Coordination epoch:** `1`
**Coordination mode:** `{mode}`
**Shared goal:** `{resolved_shared_goal}`
**Last reconciliation:** `{last_reconciliation}`
**Coordinator thread ID:** `{COORDINATOR_ID}`
**Coordinator thread name:** `Project Coordinator`
**Coordinator status:** `{coordinator_status}`
**Accepts project messages:** `{coordinator_accepts}`

## Registered sessions

{_table(registered_headers, sessions)}

## Active tasks

{_table(active_headers, active)}

## Pending commands

{_table(pending_headers, pending)}

## Paused work

{_table(paused_headers, [])}

## Resume queue

{_table(resume_headers, [])}

## Blocked decisions

{_table(blocked_headers, [])}

## Excluded tasks

{_table(["Thread ID", "Thread name", "Excluded by", "Reason", "Status"], [])}
"""


class SessionStartHookTests(unittest.TestCase):
    def test_valid_session_start_dispatches_bounded_mission_control_lifecycle(self) -> None:
        module = _load_hook_module()
        with (
            mock.patch.dict(
                os.environ,
                {"CODEX_COORDINATOR_DISABLE_MISSION_CONTROL_AUTOSTART": "0"},
            ),
            mock.patch.object(module.subprocess, "Popen") as popen,
        ):
            module._start_mission_control(REPOSITORY)

        command = popen.call_args.args[0]
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], "-I")
        self.assertEqual(Path(command[2]).name, "mission_control_lifecycle.py")
        self.assertIn("--automatic", command)
        self.assertEqual(command[-1], str(REPOSITORY))
        self.assertEqual(popen.call_args.kwargs["stdout"], subprocess.DEVNULL)

    def test_lifecycle_child_uses_isolated_installed_shape_imports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "plugin"
            scripts = plugin / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(HOOK, scripts / HOOK.name)
            shutil.copy2(PLUGIN / "scripts" / "mission_control_lifecycle.py", scripts)
            shutil.copytree(PLUGIN / "mission_control", plugin / "mission_control")
            marker = root / "shadow-executed.txt"
            shadow = (
                "import os\n"
                "open(os.environ['CODEX_SHADOW_MARKER'], 'w', encoding='utf-8').write(__file__)\n"
                "raise RuntimeError('shadow json executed')\n"
            )
            (scripts / "json.py").write_text(shadow, encoding="utf-8")
            (plugin / "json.py").write_text(shadow, encoding="utf-8")
            spec = importlib.util.spec_from_file_location(
                "isolated_session_start_fixture", scripts / HOOK.name
            )
            assert spec and spec.loader
            hook = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = hook
            spec.loader.exec_module(hook)

            with mock.patch.dict(
                os.environ,
                {"CODEX_COORDINATOR_DISABLE_MISSION_CONTROL_AUTOSTART": "0"},
            ), mock.patch.object(hook.subprocess, "Popen") as popen:
                hook._start_mission_control(REPOSITORY)

            command = popen.call_args.args[0]
            self.assertEqual(command[:2], [sys.executable, "-I"])
            environment = os.environ.copy()
            environment["CODEX_SHADOW_MARKER"] = str(marker)
            environment["PYTHONPATH"] = str(plugin)
            completed = subprocess.run(
                [*command[:3], "status", "--port", "65534"],
                cwd=plugin,
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
                env=environment,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(marker.exists(), completed.stderr)
            self.assertIn("automatic_start_enabled", json.loads(completed.stdout))

    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("Git is required for SessionStart hook tests")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def _repository(self, name: str = "repository") -> Path:
        root = self.base / name
        root.mkdir(parents=True)
        result = _run(["git", "init", "-q", str(root)])
        self.assertEqual(result.returncode, 0, result.stderr)
        return root

    def _write_state(self, root: Path, *, marker: str | None = None, current: str | None = None) -> None:
        coordination = root / ".codex" / "coordination"
        coordination.mkdir(parents=True)
        (coordination / "project.yaml").write_text(marker or _marker(), encoding="utf-8")
        (coordination / "CURRENT.md").write_text(current or _current(), encoding="utf-8")

    def _invoke(self, cwd: Path, session_id: str = WORKER_ID) -> str:
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"cwd": str(cwd), "session_id": session_id}),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout, "hook emitted no JSON")
        payload = json.loads(result.stdout)
        return payload["hookSpecificOutput"]["additionalContext"]

    def test_normal_state_reports_owned_pending_command_without_warnings(self) -> None:
        root = self._repository()
        self._write_state(root)

        context = self._invoke(root)

        self.assertIn("project_id=sample-project", context)
        self.assertIn("registered_role=TASK_AGENT", context)
        self.assertIn("state_warnings=NONE", context)
        self.assertIn("pending_commands=SAMPLE-002:MSG-001:PENDING", context)
        self.assertIn("pending_resume_actions=NONE", context)

    def test_duplicate_enablement_marker_is_reported_as_incompatible(self) -> None:
        root = self._repository("duplicate-enablement")
        marker = _marker().replace(
            "coordination_enabled: true",
            "coordination_enabled: true\ncoordination_enabled: true",
        )
        self._write_state(root, marker=marker)

        context = self._invoke(root)

        self.assertIn("marker is incompatible", context)
        self.assertIn("coordination_enabled_missing_or_invalid", context)
        self.assertIn("do not read project coordination state", context.lower())

    def test_unicode_shared_goal_and_timezone_aware_reconciliation_are_valid(self) -> None:
        root = self._repository()
        shared_goal = "समन्वय सुरक्षित रखें — बिना बदलाव खोए 🚀"
        reconciliation = "2026-07-15T17:30:45.123456+05:30"
        self._write_state(
            root,
            current=_current(
                shared_goal=shared_goal,
                last_reconciliation=reconciliation,
            ),
        )

        context = self._invoke(root)

        self.assertIn(f"shared_goal={shared_goal}", context)
        self.assertIn(f"last_reconciliation={reconciliation}", context)
        self.assertIn("state_warnings=NONE", context)

        module = _load_hook_module()
        self.assertTrue(module._valid_shared_goal("a" * 512))
        self.assertFalse(module._valid_shared_goal("a" * 513))
        self.assertFalse(module._valid_shared_goal("line\u2028break"))
        self.assertFalse(module._valid_shared_goal("unsafe\x00goal"))

    def test_legacy_shared_user_goal_label_is_not_silently_accepted(self) -> None:
        root = self._repository()
        current = _current().replace("**Shared goal:**", "**Shared user goal:**")
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("shared_goal=UNKNOWN", context)
        self.assertIn("shared_goal_missing_or_invalid", context)

    def test_duplicate_required_goal_and_reconciliation_fields_are_invalid(self) -> None:
        cases = {
            "shared-goal": (
                "**Shared goal:** `test hook behavior`",
                "**Shared goal:** `different goal`",
                "shared_goal=UNKNOWN",
                "shared_goal_missing_or_invalid",
            ),
            "last-reconciliation": (
                "**Last reconciliation:** `2026-07-15T12:00:00Z`",
                "**Last reconciliation:** `2026-07-15T13:00:00Z`",
                "last_reconciliation=UNKNOWN",
                "last_reconciliation_missing_or_invalid",
            ),
        }
        for name, (existing, duplicate, output, warning) in cases.items():
            with self.subTest(name=name):
                root = self._repository(f"duplicate-{name}")
                current = _current().replace(existing, f"{existing}\n{duplicate}")
                self._write_state(root, current=current)

                context = self._invoke(root)

                self.assertIn(output, context)
                self.assertIn(warning, context)
                self.assertNotIn("state_warnings=NONE", context)

    def test_duplicate_required_section_is_invalid_instead_of_using_first_copy(self) -> None:
        root = self._repository("duplicate-active-section")
        current = _current() + f"""

## Active tasks

| Task ID | Owner | Role | Status |
|---|---|---|---|
| SAMPLE-999 | {WORKER_ID} | TASK_AGENT | ACTIVE |
"""
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("active_tasks_section_duplicate", context)
        self.assertNotIn("state_warnings=NONE", context)

    def test_duplicate_coordinator_addresses_do_not_collapse_to_none(self) -> None:
        cases = {
            "thread-id": (
                f"**Coordinator thread ID:** `{COORDINATOR_ID}`",
                "**Coordinator thread ID:** `UNAVAILABLE`",
                "coordinator_thread_id=UNKNOWN",
                "coordinator_thread_id_missing_or_invalid",
            ),
            "thread-name": (
                "**Coordinator thread name:** `Project Coordinator`",
                "**Coordinator thread name:** `Backup Coordinator`",
                "coordinator_thread_name=UNKNOWN",
                "coordinator_thread_name_missing_or_invalid",
            ),
        }
        for name, (existing, duplicate, output, warning) in cases.items():
            with self.subTest(name=name):
                root = self._repository(f"duplicate-coordinator-{name}")
                current = _current().replace(existing, f"{existing}\n{duplicate}")
                self._write_state(root, current=current)

                context = self._invoke(root, COORDINATOR_ID)

                self.assertIn(output, context)
                self.assertIn(warning, context)
                self.assertNotIn("state_warnings=NONE", context)

        module = _load_hook_module()
        self.assertEqual(
            module._required_field(
                "**Coordinator thread ID:** `NONE`\n",
                "Coordinator thread ID",
                module.THREAD,
                "UNKNOWN",
            ),
            "NONE",
        )
        self.assertEqual(
            module._required_field(
                "**Coordinator thread name:** `NONE`\n",
                "Coordinator thread name",
                module.NAME,
                "UNKNOWN",
            ),
            "NONE",
        )

    def test_reconciliation_requires_timezone_aware_iso_8601(self) -> None:
        cases = ("2026-07-15T12:00:00", "not-a-timestamp")
        for index, reconciliation in enumerate(cases):
            with self.subTest(reconciliation=reconciliation):
                root = self._repository(f"invalid-reconciliation-{index}")
                self._write_state(
                    root,
                    current=_current(last_reconciliation=reconciliation),
                )

                context = self._invoke(root)

                self.assertIn("last_reconciliation=UNKNOWN", context)
                self.assertIn("last_reconciliation_missing_or_invalid", context)

    def test_managing_mode_is_independent_from_workload_idle(self) -> None:
        cases = {
            "goal-present": (
                _current(
                    coordinator_task="NONE",
                    coordinator_status="IDLE",
                    include_worker=False,
                    include_active_coordinator=False,
                    include_active_worker=False,
                    shared_goal="work remains",
                ),
                "shared_goal=work remains",
            ),
            "workload-idle": (
                _current(shared_goal="none"),
                "shared_goal=none",
            ),
        }
        for name, (current, expected) in cases.items():
            with self.subTest(name=name):
                root = self._repository(name)
                self._write_state(root, current=current)

                context = self._invoke(root)

                self.assertIn(expected, context)
                self.assertIn("coordination_mode=MANAGING", context)
                self.assertIn("state_warnings=NONE", context)

    def test_primary_worktree_uses_one_git_call_bounded_below_hook_timeout(self) -> None:
        root = self._repository()
        module = _load_hook_module()
        worktree_output = f"worktree {root}\0HEAD abcdef\0\0"
        completed = subprocess.CompletedProcess(["git"], 0, worktree_output, "")

        with mock.patch.object(module, "_run_git", return_value=completed) as run_git:
            primary = module._primary_worktree(root)

        self.assertEqual(primary, root.resolve())
        run_git.assert_called_once_with(root, "worktree", "list", "--porcelain", "-z")
        self.assertLess(module.GIT_TIMEOUT_SECONDS, 5)

    def test_marker_schema_and_access_are_rejected_before_current_state(self) -> None:
        cases = {
            "schema": (_marker(schema_version="2"), "unsupported_marker_schema"),
            "task-access": (_marker(task_access="true"), "cross_project_task_access_not_false"),
            "state-changes": (
                _marker(state_changes="true"),
                "cross_project_state_changes_not_false",
            ),
        }
        for name, (marker, expected) in cases.items():
            with self.subTest(name=name):
                root = self._repository(name)
                coordination = root / ".codex" / "coordination"
                coordination.mkdir(parents=True)
                (coordination / "project.yaml").write_text(marker, encoding="utf-8")
                # A directory here makes any attempted CURRENT.md read fail.
                (coordination / "CURRENT.md").mkdir()

                context = self._invoke(root)

                self.assertIn(expected, context)
                self.assertIn("marker is incompatible", context)
                self.assertNotIn("coordination_epoch=", context)

    def test_missing_current_state_keeps_the_exact_recovery_warning(self) -> None:
        root = self._repository("missing-current")
        coordination = root / ".codex" / "coordination"
        coordination.mkdir(parents=True)
        (coordination / "project.yaml").write_text(_marker(), encoding="utf-8")

        context = self._invoke(root)

        self.assertIn("state is invalid", context)
        self.assertIn("current_state_missing", context)
        self.assertIn("current_project_id_missing_or_invalid", context)

    def test_enabled_marker_internal_error_is_visible_without_details_or_authority(self) -> None:
        root = self._repository()
        coordination = root / ".codex" / "coordination"
        coordination.mkdir(parents=True)
        (coordination / "project.yaml").write_text(_marker(), encoding="utf-8")
        (coordination / "CURRENT.md").mkdir()

        context = self._invoke(root)

        self.assertIn("state_warnings=hook_internal_error", context)
        self.assertIn("this hook grants no authority", context)
        self.assertNotIn("OSError", context)
        self.assertNotIn("regular file", context)

    def test_unicode_repository_path_is_decoded_safely(self) -> None:
        root = self._repository("समन्वय-रिपॉजिटरी")
        self._write_state(root)

        context = self._invoke(root)

        self.assertIn("project_id=sample-project", context)
        self.assertIn("state_warnings=NONE", context)

    def test_non_latin_punctuated_canonical_name_works_as_fallback_address(self) -> None:
        root = self._repository()
        title = "संयोजक — समीक्षा! 🚀"
        current = _current()
        current = current.replace(
            f"**Coordinator thread ID:** `{COORDINATOR_ID}`",
            "**Coordinator thread ID:** `UNAVAILABLE`",
        )
        current = current.replace(
            f"| {COORDINATOR_ID} | Project Coordinator |",
            f"| UNAVAILABLE | {title} |",
        )
        current = current.replace(
            f"| SAMPLE-001 | {COORDINATOR_ID} |",
            f"| SAMPLE-001 | {title} |",
        )
        current = current.replace("Project Coordinator", title)
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn(f"coordinator_thread_name={title}", context)
        self.assertIn("state_warnings=NONE", context)
        module = _load_hook_module()
        self.assertEqual(module._safe("bad|name", module.NAME), "UNKNOWN")
        self.assertEqual(module._safe("bad\u2028name", module.NAME), "UNKNOWN")
        self.assertEqual(module._safe("bad\x00name", module.NAME), "UNKNOWN")

    def test_reordered_table_columns_are_resolved_by_header(self) -> None:
        root = self._repository()
        self._write_state(root, current=_current(reorder=True))

        context = self._invoke(root)

        self.assertIn("state_warnings=NONE", context)
        self.assertIn("assigned_task_id=SAMPLE-002", context)
        self.assertIn("pending_commands=SAMPLE-002:MSG-001:PENDING", context)

    def test_pending_command_accepts_exact_registered_name_fallback(self) -> None:
        root = self._repository()
        current = _current().replace(
            f"| SAMPLE-002 | MSG-001 | {WORKER_ID} | AMEND_TASK | PENDING |",
            "| SAMPLE-002 | MSG-001 | Hook Worker | AMEND_TASK | PENDING |",
        )
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("pending_commands=SAMPLE-002:MSG-001:PENDING", context)
        self.assertIn("state_warnings=NONE", context)

    def test_missing_required_header_warns_and_pending_state_is_unknown(self) -> None:
        root = self._repository()
        current = _current().replace(" | Recipient thread ID", " | Recipient")
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("pending_commands_required_headers_missing", context)
        self.assertIn("pending_commands=UNKNOWN_INVALID_STATE", context)

    def test_unknown_table_column_is_invalid(self) -> None:
        root = self._repository("unknown-column")
        current = _current().replace(
            "| Task ID | Owner | Role | Status |\n| --- | --- | --- | --- |",
            "| Task ID | Owner | Role | Status | Notes |\n| --- | --- | --- | --- | --- |",
        ).replace(
            "| SAMPLE-001 | 11111111-1111-4111-8111-111111111111 | COORDINATOR | ACTIVE |",
            "| SAMPLE-001 | 11111111-1111-4111-8111-111111111111 | COORDINATOR | ACTIVE | note |",
        ).replace(
            "| SAMPLE-002 | 22222222-2222-4222-8222-222222222222 | TASK_AGENT | ACTIVE |",
            "| SAMPLE-002 | 22222222-2222-4222-8222-222222222222 | TASK_AGENT | ACTIVE | note |",
        )
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("active_tasks_unknown_headers", context)
        self.assertIn("stale_active_task_binding", context)

    def test_renamed_table_column_is_invalid(self) -> None:
        root = self._repository("renamed-column")
        current = _current().replace("| Thread ID | Thread name |", "| Thread ID | Canonical name |")
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("registered_sessions_unknown_headers", context)
        self.assertIn("registered_sessions_required_headers_missing", context)

    def test_invalid_pending_identifier_is_unknown_not_none(self) -> None:
        root = self._repository("invalid-pending-id")
        current = _current().replace(
            "| SAMPLE-002 | MSG-001 | 22222222-2222-4222-8222-222222222222 | AMEND_TASK | PENDING |",
            "| SAMPLE-002 | bad id | 22222222-2222-4222-8222-222222222222 | AMEND_TASK | PENDING |",
        )
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("pending_commands_row_invalid", context)
        self.assertIn("pending_commands=UNKNOWN_INVALID_STATE", context)
        self.assertNotIn("pending_commands=NONE", context)

    def test_duplicate_active_task_id_is_warned(self) -> None:
        root = self._repository("duplicate-active-task-id")
        current = _current().replace(
            "| 22222222-2222-4222-8222-222222222222 | Hook Worker | PROJECT_EXECUTION | TASK_AGENT | SAMPLE-002 | ACTIVE | true |",
            "| 22222222-2222-4222-8222-222222222222 | Hook Worker | PROJECT_EXECUTION | TASK_AGENT | SAMPLE-001 | ACTIVE | true |",
        ).replace(
            "| SAMPLE-002 | 22222222-2222-4222-8222-222222222222 | TASK_AGENT | ACTIVE |",
            "| SAMPLE-001 | 22222222-2222-4222-8222-222222222222 | TASK_AGENT | ACTIVE |",
        ).replace(
            "| SAMPLE-002 | MSG-001 | 22222222-2222-4222-8222-222222222222 | AMEND_TASK | PENDING |",
            "| SAMPLE-001 | MSG-001 | 22222222-2222-4222-8222-222222222222 | AMEND_TASK | PENDING |",
        )
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("active_tasks_duplicate_task_id", context)
        self.assertIn("stale_active_task_binding", context)

    def test_invalid_native_session_id_is_visible(self) -> None:
        root = self._repository("invalid-session-id")
        self._write_state(root)

        context = self._invoke(root, session_id="not a uuid")

        self.assertIn("this_session_id=UNKNOWN", context)
        self.assertIn("this_session_id_missing_or_invalid", context)

    def test_terminal_owner_is_not_accepted_for_an_active_task(self) -> None:
        root = self._repository()
        self._write_state(
            root,
            current=_current(worker_status="COMPLETE", worker_accepts="false"),
        )

        context = self._invoke(root)

        self.assertIn("active_task_owner_terminal", context)
        self.assertIn("active_task_owner_not_accepting", context)
        self.assertIn("stale_active_task_binding", context)

    def test_stale_active_task_binding_detects_owner_task_mismatch(self) -> None:
        root = self._repository()
        self._write_state(root, current=_current(worker_task="SAMPLE-009"))

        context = self._invoke(root)

        self.assertIn("active_task_owner_task_mismatch", context)
        self.assertIn("stale_active_task_binding", context)

    def test_accepting_registered_task_must_exist_in_active_tasks(self) -> None:
        root = self._repository()
        self._write_state(root, current=_current(include_active_worker=False))

        context = self._invoke(root)

        self.assertIn("registered_task_missing_from_active_tasks", context)
        self.assertIn("stale_active_task_binding", context)

    def test_reusable_idle_coordinator_without_active_task_is_valid(self) -> None:
        root = self._repository()
        self._write_state(
            root,
            current=_current(
                coordinator_task="NONE",
                coordinator_status="IDLE",
                include_worker=False,
                include_active_coordinator=False,
                include_active_worker=False,
            ),
        )

        context = self._invoke(root, COORDINATOR_ID)

        self.assertIn("coordination_mode=MANAGING", context)
        self.assertIn("assigned_task_id=NONE", context)
        self.assertIn("state_warnings=NONE", context)

    def test_active_user_exclusions_are_reported_in_restart_context(self) -> None:
        root = self._repository()
        exclusion_table = (
            "## Excluded tasks\n\n"
            + _table(["Thread ID", "Thread name", "Excluded by", "Reason", "Status"], [])
        )
        excluded = _table(
            ["Thread ID", "Thread name", "Excluded by", "Reason", "Status"],
            [
                {
                    "Thread ID": WORKER_ID,
                    "Thread name": "Private task",
                    "Excluded by": "DIRECT_USER",
                    "Reason": "User requested isolation",
                    "Status": "ACTIVE",
                }
            ],
        )
        current = _current().replace(exclusion_table, "## Excluded tasks\n\n" + excluded)
        self._write_state(root, current=current)

        context = self._invoke(root, COORDINATOR_ID)

        self.assertIn(f"excluded_tasks={WORKER_ID}", context)
        self.assertIn("state_warnings=NONE", context)

    def test_harmless_idle_aliases_normalize_without_weakening_ownership_checks(self) -> None:
        root = self._repository()
        current = _current(
            coordinator_task="-",
            coordinator_status="IDLE",
            include_worker=False,
            include_active_coordinator=False,
            include_active_worker=False,
            shared_goal="No active coordinated goal.",
        )
        self._write_state(
            root,
            current=current,
        )

        context = self._invoke(root, COORDINATOR_ID)

        self.assertIn("shared_goal=none", context)
        self.assertIn("assigned_task_id=NONE", context)
        self.assertIn("state_warnings=NONE", context)

    def test_initial_unregistered_state_accepts_installation_name(self) -> None:
        root = self._repository()
        current = _current(
            coordinator_task="NONE",
            coordinator_status="UNREGISTERED",
            coordinator_accepts="false",
            include_worker=False,
            include_active_coordinator=False,
            include_active_worker=False,
        )
        current = current.replace(
            f"**Coordinator thread ID:** `{COORDINATOR_ID}`",
            "**Coordinator thread ID:** `NONE`",
        ).replace(
            "**Coordinator thread name:** `Project Coordinator`",
            "**Coordinator thread name:** `UNREGISTERED`",
        )
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("coordinator_thread_id=NONE", context)
        self.assertIn("coordinator_thread_name=UNREGISTERED", context)
        self.assertIn("state_warnings=enabled_project_coordinator_not_active", context)

    def test_terminal_nonaccepting_coordinator_header_is_stale_without_active_task(self) -> None:
        root = self._repository()
        self._write_state(
            root,
            current=_current(
                coordinator_task="NONE",
                coordinator_status="COMPLETE",
                coordinator_accepts="false",
                include_worker=False,
                include_active_coordinator=False,
                include_active_worker=False,
            ),
        )

        context = self._invoke(root, COORDINATOR_ID)

        self.assertIn("coordinator_header_terminal", context)
        self.assertIn("coordinator_header_not_accepting", context)
        self.assertIn("stale_coordinator_binding", context)

    def test_coordinator_header_status_and_acceptance_must_match_registration(self) -> None:
        root = self._repository()
        self._write_state(
            root,
            current=_current(
                coordinator_task="NONE",
                coordinator_status="IDLE",
                coordinator_accepts="true",
                coordinator_row_status="ACTIVE",
                coordinator_row_accepts="false",
                include_worker=False,
                include_active_coordinator=False,
                include_active_worker=False,
            ),
        )

        context = self._invoke(root, COORDINATOR_ID)

        self.assertIn("coordinator_header_status_mismatch", context)
        self.assertIn("coordinator_header_acceptance_mismatch", context)
        self.assertIn("stale_coordinator_binding", context)

    def test_coordinator_task_binding_and_idle_status_must_agree(self) -> None:
        cases = {
            "taskless-active": (
                _current(
                    coordinator_task="NONE",
                    coordinator_status="ACTIVE",
                    include_worker=False,
                    include_active_coordinator=False,
                    include_active_worker=False,
                ),
                "coordinator_without_task_not_idle",
            ),
            "task-bound-idle": (
                _current(
                    coordinator_task="SAMPLE-001",
                    coordinator_status="IDLE",
                    include_worker=False,
                    include_active_worker=False,
                ),
                "coordinator_with_task_marked_idle",
            ),
        }
        for name, (current, expected) in cases.items():
            with self.subTest(name=name):
                root = self._repository(name)
                self._write_state(root, current=current)

                context = self._invoke(root, COORDINATOR_ID)

                self.assertIn(expected, context)
                self.assertIn("stale_coordinator_binding", context)

    def test_truncated_state_never_reports_pending_output_as_none(self) -> None:
        root = self._repository()
        current = _current()
        insertion = "\n## Long notes\n\n" + ("x" * 40_000) + "\n"
        current = current.replace("\n## Pending commands\n", insertion + "\n## Pending commands\n")
        self._write_state(root, current=current)

        context = self._invoke(root)

        self.assertIn("current_state_truncated", context)
        self.assertIn("pending_commands=UNKNOWN_TRUNCATED", context)
        self.assertIn("pending_resume_actions=UNKNOWN_TRUNCATED", context)
        self.assertNotIn("pending_commands=NONE", context)

    def test_linked_worktree_reads_only_primary_state(self) -> None:
        root = self._repository("primary")
        _run(["git", "config", "user.email", "hook-test@example.invalid"], cwd=root)
        _run(["git", "config", "user.name", "Hook Test"], cwd=root)
        (root / "tracked.txt").write_text("fixture\n", encoding="utf-8")
        self.assertEqual(_run(["git", "add", "tracked.txt"], cwd=root).returncode, 0)
        commit = _run(["git", "commit", "-q", "-m", "fixture"], cwd=root)
        self.assertEqual(commit.returncode, 0, commit.stderr)
        linked = self.base / "linked"
        add = _run(["git", "worktree", "add", "-q", "-b", "linked-test", str(linked)], cwd=root)
        self.assertEqual(add.returncode, 0, add.stderr)
        self._write_state(root)

        context = self._invoke(linked)

        self.assertIn("project_id=sample-project", context)
        self.assertIn("state_warnings=NONE", context)

    def test_hook_is_packaged_at_default_path_with_plugin_root_commands(self) -> None:
        old_config = PLUGIN / "hooks.json"
        config_path = PLUGIN / "hooks" / "hooks.json"
        self.assertFalse(old_config.exists())
        self.assertTrue(config_path.is_file())
        config = json.loads(config_path.read_text(encoding="utf-8"))
        hook = config["hooks"]["SessionStart"][0]["hooks"][0]
        expected = '${PLUGIN_ROOT}/scripts/codex_coordinator_session_start.py'
        self.assertIn(expected, hook["command"])
        self.assertIn(expected, hook["commandWindows"])
        self.assertIn("codex_coordinator_bootstrap.sh", hook["command"])
        self.assertIn("codex_coordinator_bootstrap.ps1", hook["commandWindows"])
        self.assertGreaterEqual(hook["timeout"], 120)
        self.assertNotIn("./scripts/", hook["command"])
        self.assertNotIn("./scripts/", hook["commandWindows"])
        self.assertTrue(HOOK.is_file())
        self.assertNotIn("shell=True", HOOK.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
