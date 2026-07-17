import json
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from pathlib import Path
from unittest import mock

from apps.mission_control.collector import (
    CodexThreadReader,
    Collector,
    DoctorRunner,
    Settings,
    SettingsStore,
    _epoch_datetime,
    _extract_patch_paths,
    _local_date,
)
from apps.mission_control.server import MissionControlRuntime, MissionControlServer


THREAD_ONE = "11111111-1111-4111-8111-111111111111"
THREAD_TWO = "22222222-2222-4222-8222-222222222222"
THREAD_THREE = "33333333-3333-4333-8333-333333333333"
THREAD_FOUR = "44444444-4444-4444-8444-444444444444"


class MissionControlFixture:
    def __init__(self, root: Path):
        self.root = root
        self.project = root / "sample-project"
        self.codex_home = root / "codex-home"
        self.data_dir = root / "app-data"
        self.coordination = self.project / ".codex" / "coordination"
        (self.coordination / "tasks").mkdir(parents=True)
        self.codex_home.mkdir()
        (self.coordination / "project.yaml").write_text(
            "schema_version: 1\nproject_id: sample-project\ncoordination_enabled: true\n",
            encoding="utf-8",
        )
        (self.coordination / "CURRENT.md").write_text(
            f"""# Codex Coordinator state

**Project ID:** sample-project
**Coordination epoch:** 2
**Coordination mode:** ACTIVE
**Shared goal:** Ship the dashboard
**Last reconciliation:** 2026-07-16T12:00:00Z

## Registered sessions

| Thread ID | Thread name | Scope kind | Role | Task ID | Status | Accepts project messages |
|---|---|---|---|---|---|---|
| {THREAD_ONE} | Interface agent | PROJECT_EXECUTION | TASK_AGENT | MC-001 | ACTIVE | true |
| {THREAD_TWO} | Collector agent | PROJECT_EXECUTION | TASK_AGENT | MC-002 | ACTIVE | true |

## Active tasks

| Task ID | Owner | Role | Status |
|---|---|---|---|
| MC-001 | Interface agent | TASK_AGENT | ACTIVE |
| MC-002 | Collector agent | TASK_AGENT | ACTIVE |

## Pending commands

| Task ID | Message ID | Recipient thread ID | Message type | Status |
|---|---|---|---|---|

## Paused work

| Task ID | Owner | Reason | Resume condition | Status |
|---|---|---|---|---|

## Resume queue

| Task ID | Message ID | Resume condition | Status |
|---|---|---|---|

## Blocked decisions

| Decision ID | Task ID | Decision needed | Status |
|---|---|---|---|
""",
            encoding="utf-8",
        )
        (self.coordination / "tasks" / "MC-001.md").write_text(
            "**Individual goal:** Build the live task workboard.\n"
            "**Exact write paths:** apps/mission_control/static\n",
            encoding="utf-8",
        )
        (self.coordination / "tasks" / "MC-002.md").write_text(
            "**Individual goal:** Connect the local collector.\n"
            "**Exact write paths:** apps/mission_control/static/app.js\n",
            encoding="utf-8",
        )
        self._create_codex_state()

    def _create_codex_state(self):
        rollout_one = self.codex_home / "one.jsonl"
        rollout_two = self.codex_home / "two.jsonl"
        rollout_one.write_text(
            json.dumps(
                {
                    "timestamp": "2026-07-16T12:00:00Z",
                    "type": "event_msg",
                    "payload": {"type": "agent_message", "message": "Building the workboard now.", "phase": "commentary"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        rollout_two.write_text(
            json.dumps(
                {
                    "timestamp": "2026-07-16T12:00:00Z",
                    "type": "event_msg",
                    "payload": {"type": "agent_message", "message": "Reading local receipts.", "phase": "commentary"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        database = sqlite3.connect(self.codex_home / "state_5.sqlite")
        database.execute(
            """CREATE TABLE threads (
                id TEXT PRIMARY KEY, rollout_path TEXT NOT NULL, created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL, cwd TEXT NOT NULL, title TEXT NOT NULL,
                tokens_used INTEGER NOT NULL DEFAULT 0, archived INTEGER NOT NULL DEFAULT 0,
                agent_nickname TEXT, agent_role TEXT, model TEXT, reasoning_effort TEXT,
                first_user_message TEXT
            )"""
        )
        now = int(time.time())
        rows = [
            (THREAD_ONE, str(rollout_one), now - 60, now, str(self.project), "Build dashboard", 100, 0, "Nova", "task_agent", "gpt-test", "low", ""),
            (THREAD_TWO, str(rollout_two), now - 60, now, str(self.project), "Build collector", 100, 0, "Orbit", "task_agent", "gpt-test", "low", ""),
        ]
        database.executemany("INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        database.commit()
        database.close()
        (self.codex_home / "session_index.jsonl").write_text(
            json.dumps({"id": THREAD_ONE, "thread_name": "Build the live workboard"})
            + "\n"
            + json.dumps({"id": THREAD_TWO, "thread_name": "Connect the collector"})
            + "\n",
            encoding="utf-8",
        )


class CollectorTests(unittest.TestCase):
    def test_user_message_stays_queued_until_agent_work_begins(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = MissionControlFixture(Path(directory))
            rollout = fixture.codex_home / "one.jsonl"
            rollout.write_text(
                json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}})
                + "\n"
                + json.dumps({"type": "event_msg", "payload": {"type": "task_started"}})
                + "\n"
                + json.dumps(
                    {
                        "type": "response_item",
                        "payload": {"type": "message", "role": "user"},
                    }
                )
                + "\n"
                + json.dumps({"type": "event_msg", "payload": {"type": "user_message"}})
                + "\n",
                encoding="utf-8",
            )

            receipt = CodexThreadReader._rollout_receipt(rollout)
            self.assertFalse(receipt["complete"])
            self.assertFalse(receipt["turnEnded"])
            self.assertTrue(receipt["pendingUserMessage"])

            rows = CodexThreadReader(fixture.codex_home).read()
            self.assertEqual(next(row for row in rows if row["threadId"] == THREAD_ONE)["status"], "queued")
            snapshot = Collector([fixture.project], codex_home=fixture.codex_home).collect()
            queued = next(task for task in snapshot["tasks"] if task["openUrl"].endswith(THREAD_ONE))
            self.assertEqual(queued["status"], "queued")
            self.assertEqual(snapshot["metrics"]["active"], 2)
            self.assertEqual(snapshot["conflicts"], [])

            with rollout.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "type": "response_item",
                            "payload": {"type": "reasoning"},
                        }
                    )
                    + "\n"
                )

            receipt = CodexThreadReader._rollout_receipt(rollout)
            self.assertFalse(receipt["pendingUserMessage"])
            rows = CodexThreadReader(fixture.codex_home).read()
            self.assertEqual(next(row for row in rows if row["threadId"] == THREAD_ONE)["status"], "active")

    def test_invalid_local_timestamps_and_receipt_rows_fail_safe(self):
        epoch = datetime.fromtimestamp(0, timezone.utc)
        for value in (float("nan"), float("inf"), -float("inf"), 10**30):
            with self.subTest(value=value):
                self.assertEqual(_epoch_datetime(value), epoch)

        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            rollout.write_text(
                "[]\n"
                + json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {"type": "turn_aborted"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            receipt = CodexThreadReader._rollout_receipt(rollout)
            self.assertFalse(receipt["complete"])
            self.assertTrue(receipt["turnEnded"])

    def test_invalid_settings_json_shape_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "settings.json").write_text("[]", encoding="utf-8")

            self.assertEqual(SettingsStore(data_dir).get(), Settings())

    def test_collects_human_tasks_and_declared_overlap_without_display_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = MissionControlFixture(Path(directory))
            database = sqlite3.connect(fixture.codex_home / "state_5.sqlite")
            database.execute(
                "UPDATE threads SET first_user_message = ? WHERE id = ?",
                (
                    "<codex_delegation>\n**Individual goal:** Coordinate a long internal implementation goal.\n</codex_delegation>",
                    THREAD_ONE,
                ),
            )
            database.commit()
            database.close()
            snapshot = Collector([fixture.project], codex_home=fixture.codex_home).collect()

            titles = {task["title"] for task in snapshot["tasks"]}
            self.assertIn("Build the live workboard", titles)
            self.assertIn("Connect the collector", titles)
            goals = {task["coordinationGoal"] for task in snapshot["tasks"]}
            self.assertIn("Build the live task workboard.", goals)
            self.assertIn("Connect the local collector.", goals)
            self.assertEqual(snapshot["metrics"]["active"], 2)
            self.assertEqual(snapshot["metrics"]["attention"], 2)
            self.assertEqual(snapshot["metrics"]["overlaps"], 1)
            self.assertEqual(snapshot["conflicts"][0]["title"], "Declared scopes collide")
            self.assertEqual(snapshot["conflicts"][0]["confidence"], "declared")
            self.assertIn("Confirm one owner", snapshot["conflicts"][0]["action"])
            serialized = json.dumps(snapshot)
            self.assertNotIn('"taskId"', serialized)
            self.assertNotIn('"threadId"', serialized)
            self.assertIn("codex://threads/", serialized)

    def test_filters_general_chats_and_discovers_other_coordinator_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = MissionControlFixture(Path(directory))
            other_project = fixture.root / "other-project"
            other_coordination = other_project / ".codex" / "coordination"
            other_coordination.mkdir(parents=True)
            (other_coordination / "project.yaml").write_text(
                "schema_version: 1\nproject_id: other-project\ncoordination_enabled: true\n",
                encoding="utf-8",
            )

            general_chat = fixture.root / "salary-estimate"
            (general_chat / ".git").mkdir(parents=True)
            other_rollout = fixture.codex_home / "other-project.jsonl"
            chat_rollout = fixture.codex_home / "general-chat.jsonl"
            receipt = json.dumps(
                {
                    "timestamp": "2026-07-16T12:00:00Z",
                    "type": "event_msg",
                    "payload": {"type": "agent_message", "message": "Working now.", "phase": "commentary"},
                }
            ) + "\n"
            other_rollout.write_text(receipt, encoding="utf-8")
            chat_rollout.write_text(receipt, encoding="utf-8")

            database = sqlite3.connect(fixture.codex_home / "state_5.sqlite")
            now = int(time.time())
            rows = [
                (
                    THREAD_THREE,
                    str(other_rollout),
                    now - 60,
                    now,
                    str(other_project),
                    "Ship another project",
                    100,
                    0,
                    "Sage",
                    "task_agent",
                    "gpt-test",
                    "low",
                    "",
                ),
                (
                    THREAD_FOUR,
                    str(chat_rollout),
                    now - 60,
                    now,
                    str(general_chat),
                    "Estimate a salary",
                    100,
                    0,
                    "Muse",
                    "task_agent",
                    "gpt-test",
                    "low",
                    "",
                ),
            ]
            database.executemany("INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
            database.commit()
            database.close()

            snapshot = Collector([fixture.project], codex_home=fixture.codex_home).collect()

            titles = {task["title"] for task in snapshot["tasks"]}
            self.assertIn("Ship another project", titles)
            self.assertNotIn("Estimate a salary", titles)
            self.assertEqual({project["id"] for project in snapshot["projects"]}, {"sample-project", "other-project"})
            self.assertEqual(snapshot["metrics"]["active"], 3)
            self.assertEqual(snapshot["source"]["coordinationProjects"], 2)

    def test_disabled_project_does_not_leak_old_coordinator_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = MissionControlFixture(Path(directory))
            (fixture.coordination / "project.yaml").write_text(
                "schema_version: 1\nproject_id: sample-project\ncoordination_enabled: false\n",
                encoding="utf-8",
            )

            snapshot = Collector([fixture.project], codex_home=fixture.codex_home).collect()

            self.assertEqual(snapshot["tasks"], [])
            self.assertEqual(snapshot["metrics"]["active"], 0)
            self.assertEqual(snapshot["source"]["coordinationProjects"], 0)

    def test_aborted_and_stale_incomplete_tasks_are_idle_not_done(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = MissionControlFixture(Path(directory))
            now = datetime.now(timezone.utc)
            aborted_rollout = fixture.codex_home / "aborted.jsonl"
            stale_rollout = fixture.codex_home / "stale.jsonl"
            aborted_rollout.write_text(
                json.dumps({"type": "event_msg", "payload": {"type": "turn_aborted"}}) + "\n",
                encoding="utf-8",
            )
            stale_rollout.write_text(
                json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {"type": "agent_message", "message": "Still incomplete."},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            database = sqlite3.connect(fixture.codex_home / "state_5.sqlite")
            database.executemany(
                "INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        THREAD_THREE,
                        str(aborted_rollout),
                        int(now.timestamp()) - 60,
                        int(now.timestamp()),
                        str(fixture.project),
                        "Aborted task",
                        0,
                        0,
                        "Sage",
                        "task_agent",
                        "gpt-test",
                        "low",
                        "",
                    ),
                    (
                        THREAD_FOUR,
                        str(stale_rollout),
                        int(now.timestamp()) - 3600,
                        int(now.timestamp()) - 31 * 60,
                        str(fixture.project),
                        "Stale incomplete task",
                        0,
                        0,
                        "Muse",
                        "task_agent",
                        "gpt-test",
                        "low",
                        "",
                    ),
                ],
            )
            database.commit()
            database.close()

            rows = CodexThreadReader(fixture.codex_home, now=now).read()
            by_title = {row["title"]: row for row in rows}
            self.assertEqual(by_title["Aborted task"]["status"], "idle")
            self.assertFalse(by_title["Aborted task"]["receiptComplete"])
            self.assertEqual(by_title["Stale incomplete task"]["status"], "idle")
            self.assertFalse(by_title["Stale incomplete task"]["receiptComplete"])

            truncated_turn = fixture.codex_home / "truncated-turn.jsonl"
            truncated_turn.write_text(
                json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}})
                + "\n"
                + json.dumps(
                    {
                        "type": "event_msg",
                        "payload": {"type": "agent_message", "message": "A newer turn is running."},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertFalse(CodexThreadReader._rollout_receipt(truncated_turn)["complete"])

            snapshot = Collector([fixture.project], codex_home=fixture.codex_home).collect()
            self.assertEqual(snapshot["metrics"]["completedToday"], 0)

    def test_completed_today_uses_the_reviewers_local_calendar_day(self):
        india = timezone(timedelta(hours=5, minutes=30))
        just_after_midnight_local = datetime(2026, 7, 16, 19, 15, tzinfo=timezone.utc)
        self.assertEqual(
            _local_date(just_after_midnight_local, india),
            datetime(2026, 7, 17).date(),
        )

    def test_same_project_without_path_evidence_is_not_an_overlap(self):
        tasks = [
            {
                "key": "left",
                "title": "Review the dashboard",
                "project": "Sample",
                "projectPath": "C:/sample",
                "status": "active",
                "ownedPaths": [],
                "observedPaths": [],
                "coordinated": False,
            },
            {
                "key": "right",
                "title": "Check the collector",
                "project": "Sample",
                "projectPath": "C:/sample",
                "status": "active",
                "ownedPaths": [],
                "observedPaths": [],
                "coordinated": False,
            },
        ]
        self.assertEqual(Collector._conflicts(tasks), [])

    def test_same_project_subdirectory_threads_share_one_conflict_boundary(self):
        projects = [
            {
                "id": "sample",
                "name": "Sample",
                "path": str(Path("C:/sample")),
                "enabled": True,
            }
        ]
        threads = [
            {
                "threadId": THREAD_ONE,
                "title": "Edit from root",
                "projectPath": str(Path("C:/sample")),
                "status": "active",
                "owner": "One",
                "role": "Codex agent",
                "updatedAt": "2026-07-16T12:00:00Z",
                "latestUpdate": "Working.",
                "observedPaths": ["src/shared.py"],
                "receiptComplete": False,
            },
            {
                "threadId": THREAD_TWO,
                "title": "Edit from subdirectory",
                "projectPath": str(Path("C:/sample/src")),
                "status": "active",
                "owner": "Two",
                "role": "Codex agent",
                "updatedAt": "2026-07-16T12:00:00Z",
                "latestUpdate": "Working.",
                "observedPaths": ["src/shared.py"],
                "receiptComplete": False,
            },
        ]
        coordinated = [
            {
                "taskId": "MC-ONE",
                "threadId": THREAD_ONE,
                "title": "Own shared file",
                "projectId": "sample",
                "projectPath": str(Path("C:/sample")),
                "status": "active",
                "owner": "One",
                "role": "Codex agent",
                "ownedPaths": ["src/shared.py"],
                "reason": "",
            },
            {
                "taskId": "MC-TWO",
                "threadId": THREAD_TWO,
                "title": "Also own shared file",
                "projectId": "sample",
                "projectPath": str(Path("C:/sample")),
                "status": "active",
                "owner": "Two",
                "role": "Codex agent",
                "ownedPaths": ["src/shared.py"],
                "reason": "",
            },
        ]

        tasks = Collector._merge_threads(threads, coordinated, projects)

        self.assertEqual({task["projectPath"] for task in tasks}, {str(Path("C:/sample"))})
        self.assertEqual(len(Collector._conflicts(tasks)), 1)

    def test_observed_edit_crossing_another_tasks_declared_scope_is_a_conflict(self):
        tasks = [
            {
                "key": "owner",
                "title": "Own shared file",
                "project": "Sample",
                "projectPath": "C:/sample",
                "status": "active",
                "ownedPaths": ["src/shared.py"],
                "observedPaths": [],
                "coordinated": True,
            },
            {
                "key": "editor",
                "title": "Edit shared file",
                "project": "Sample",
                "projectPath": "C:/sample",
                "status": "active",
                "ownedPaths": [],
                "observedPaths": ["src/shared.py"],
                "coordinated": False,
            },
        ]

        conflicts = Collector._conflicts(tasks)

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["title"], "Work crossed a declared scope")
        self.assertEqual(conflicts[0]["confidence"], "observed")

    def test_recorded_apply_patch_paths_create_an_actionable_overlap(self):
        receipt = "*** Begin Patch\n*** Update File: apps/mission_control/static/app.js\n*** End Patch"
        self.assertEqual(_extract_patch_paths(receipt), ["apps/mission_control/static/app.js"])
        tasks = [
            {
                "key": "left",
                "title": "Simplify cards",
                "project": "Sample",
                "projectPath": "C:/sample",
                "status": "active",
                "ownedPaths": [],
                "observedPaths": _extract_patch_paths(receipt),
                "coordinated": False,
            },
            {
                "key": "right",
                "title": "Wire filters",
                "project": "Sample",
                "projectPath": "C:/sample",
                "status": "active",
                "ownedPaths": [],
                "observedPaths": ["apps/mission_control/static/app.js"],
                "coordinated": False,
            },
        ]
        conflicts = Collector._conflicts(tasks)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["confidence"], "observed")
        self.assertEqual(conflicts[0]["title"], "Same path is being edited")
        self.assertIn("Pause one task", conflicts[0]["action"])

    def test_settings_validate_and_persist_user_cadence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            settings = store.update({"refresh_seconds": 900})
            self.assertEqual(settings.refresh_seconds, 900)
            self.assertEqual(SettingsStore(Path(directory)).get(), settings)
            with self.assertRaises(ValueError):
                store.update({"refresh_seconds": 13})
            with self.assertRaises(ValueError):
                store.update({"agent_enabled": False})

    def test_obsolete_agent_settings_are_ignored_when_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "settings.json").write_text(
                json.dumps({"refresh_seconds": 300, "agent_model": "gpt-5.4-mini"}),
                encoding="utf-8",
            )
            self.assertEqual(SettingsStore(data_dir).get(), Settings(refresh_seconds=300))

    def test_manual_doctor_run_is_ephemeral_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            source_root = root / "source"
            codex_home = root / "codex-home"
            source_root.mkdir()
            codex_home.mkdir()
            runner = DoctorRunner(data_dir, source_root, codex_home)
            snapshot = {
                "projects": [{"id": "sample", "path": str(root / "sample"), "enabled": True}],
                "tasks": [
                    {
                        "projectId": "sample",
                        "projectPath": str(root / "sample"),
                        "status": "active",
                        "coordinated": True,
                        "openUrl": "codex://threads/example",
                    }
                ],
            }

            def complete(command, **kwargs):
                output = Path(command[command.index("--output-last-message") + 1])
                output.write_text(
                    "- Installed Coordinator is current.\n"
                    "- One enabled project checked; no findings.\n"
                    "DOCTOR_HEALTH: healthy",
                    encoding="utf-8",
                )
                return mock.Mock(returncode=0, stderr="", stdout="tokens used 1,234")

            with mock.patch("apps.mission_control.collector.subprocess.run", side_effect=complete) as run:
                self.assertTrue(runner.run(snapshot))

            command = run.call_args.args[0]
            prompt = run.call_args.kwargs["input"]
            self.assertIn("--ephemeral", command)
            self.assertEqual(command[command.index("--model") + 1], "gpt-5.6-sol")
            self.assertEqual(command[command.index("--sandbox") + 1], "danger-full-access")
            self.assertEqual(command[command.index("--ask-for-approval") + 1], "never")
            self.assertLess(command.index("--sandbox"), command.index("exec"))
            self.assertLess(command.index("--ask-for-approval"), command.index("exec"))
            self.assertIn('model_reasoning_effort="xhigh"', command)
            self.assertIn("Do not create, message, wake", prompt)
            self.assertIn("codex_coordinator_doctor.py --apply", prompt)
            self.assertIn("repeat it with --check", prompt)
            self.assertIn("installed global Coordinator skill", prompt)
            self.assertIn("exact SessionStart hook", prompt)
            self.assertIn("Do not run the source repository test suite", prompt)
            self.assertIn("or test Mission Control itself", prompt)
            self.assertNotIn("--mission-control-root", prompt)
            self.assertNotIn("--project-health-in", prompt)
            self.assertNotIn("--mermaid-out", prompt)
            self.assertIn("UNATTENDED_RETURN_PATH", prompt)
            self.assertIn("verified absence of an enabled heartbeat", prompt)
            self.assertIn("DOCTOR_HEALTH: healthy", prompt)
            self.assertNotIn("full unittest suite", prompt)
            self.assertIn(str(runner.source_root), prompt)
            state = runner.read_state()
            self.assertEqual(state["lastResult"], "success")
            self.assertFalse(state["running"])
            self.assertEqual(state["tokensUsed"], 1234)
            self.assertIn("One enabled project checked", state["summary"])
            self.assertEqual(state["health"], "healthy")
            self.assertEqual(len(state["bullets"]), 2)

    def test_doctor_legacy_summary_only_shows_green_for_explicitly_clear_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            data_dir.mkdir()
            runner = DoctorRunner(data_dir, root / "source", root / "codex-home")
            state_path = data_dir / "doctor-state.json"

            state_path.write_text(
                json.dumps(
                    {
                        "lastResult": "success",
                        "lastRunAt": "2026-07-17T09:00:00Z",
                        "summary": "Checks passed. New findings written: 1 medium finding. Projects needing review: sample.",
                    }
                ),
                encoding="utf-8",
            )
            review_state = runner.read_state()
            self.assertEqual(review_state["health"], "review")
            self.assertLessEqual(len(review_state["bullets"]), 3)
            self.assertTrue(any("finding" in bullet.lower() for bullet in review_state["bullets"]))

            state_path.write_text(
                json.dumps(
                    {
                        "lastResult": "success",
                        "lastRunAt": "2026-07-17T09:00:00Z",
                        "summary": "Checks passed. One project checked; no findings.",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(runner.read_state()["health"], "healthy")

    def test_manual_doctor_never_downgrades_when_cli_is_too_old(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = DoctorRunner(root / "data", root / "source", root / "codex-home")
            runner.source_root.mkdir()
            runner.codex_home.mkdir()
            incompatible = mock.Mock(
                returncode=1,
                stderr="The 'gpt-5.6-sol' model requires a newer version of Codex.",
                stdout="",
            )

            with mock.patch(
                "apps.mission_control.collector.subprocess.run",
                return_value=incompatible,
            ) as run:
                self.assertFalse(runner.run({"projects": [], "tasks": []}))

            run.assert_called_once()
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--model") + 1], "gpt-5.6-sol")
            state = runner.read_state()
            self.assertEqual(state["lastResult"], "failed")
            self.assertEqual(state["model"], "gpt-5.6-sol")
            self.assertIn("newer Codex CLI", state["error"])
            self.assertIn("will not downgrade", state["error"])

    def test_interrupted_doctor_run_is_recovered_on_server_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            data_dir.mkdir()
            (data_dir / "doctor-state.json").write_text(
                json.dumps(
                    {
                        "lastRunAt": "2026-07-17T08:00:00Z",
                        "lastResult": "running",
                        "model": "gpt-5.6-sol",
                        "reasoning": "xhigh",
                    }
                ),
                encoding="utf-8",
            )
            runner = DoctorRunner(data_dir, root / "source", root / "codex-home")

            runner.recover_interrupted_run()

            state = runner.read_state()
            self.assertEqual(state["lastResult"], "failed")
            self.assertFalse(state["running"])
            self.assertIn("interrupted by a Mission Control restart", state["error"])


class ServerTests(unittest.TestCase):
    def test_background_launcher_opens_browser_only_when_requested(self):
        launcher = Path("apps/mission_control/start-background.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$Open", launcher)
        self.assertEqual(launcher.count("Start-Process $url"), 2)
        self.assertEqual(launcher.count("if ($Open)"), 2)
        self.assertNotIn("if ($existing -and $existing.CommandLine -match 'apps\\.mission_control') {\n        Start-Process $url", launcher)
        self.assertIn("Get-NetTCPConnection", launcher)
        self.assertIn("$readyOwner -eq $process.Id", launcher)
        stopper = Path("apps/mission_control/stop.ps1").read_text(encoding="utf-8")
        self.assertIn("Get-NetTCPConnection", stopper)
        self.assertIn("Stop-MissionControlProcess", stopper)

    def test_runtime_scans_never_expose_or_start_an_agent_brief(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = MissionControlFixture(Path(directory))
            runtime = MissionControlRuntime([fixture.project], fixture.codex_home, fixture.data_dir)
            runtime.start()
            try:
                self.assertNotIn("agent", runtime.get_snapshot())

                with (fixture.codex_home / "one.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "timestamp": "2026-07-16T12:01:00Z",
                                "type": "event_msg",
                                "payload": {"type": "agent_message", "message": "The workboard changed."},
                            }
                        )
                        + "\n"
                    )
                self.assertNotIn("agent", runtime.scan())
                self.assertFalse(hasattr(runtime, "agent"))
            finally:
                runtime.stop()

    def test_local_api_and_static_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = MissionControlFixture(Path(directory))
            runtime = MissionControlRuntime([fixture.project], fixture.codex_home, fixture.data_dir)
            runtime.start()
            server = MissionControlServer(("127.0.0.1", 0), runtime)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urllib.request.urlopen(base + "/api/health", timeout=5) as response:
                    health = json.load(response)
                    self.assertEqual(health["scope"], "localhost")
                    self.assertEqual(health["doctorContractVersion"], 1)
                    self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                with urllib.request.urlopen(base + "/", timeout=5) as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("Tasks in motion", html)
                    self.assertIn("active or queued tasks", html)
                    self.assertIn("Action center", html)
                    self.assertIn("Run Doctor", html)
                    self.assertIn("Runs with GPT-5.6 Sol · Extra High reasoning", html)
                    self.assertIn('id="doctor-health-icon"', html)
                    self.assertIn('<ul class="doctor-summary"', html)
                    self.assertNotIn('id="doctor-diagnostic"', html)
                    self.assertIn("Help shape Coordinator", html)
                    self.assertIn("https://t.me/+ra4BQ7-_5uM2MDY1", html)
                    self.assertIn("Join on Telegram", html)
                    self.assertNotIn("feedback-dismiss", html)
                    self.assertNotIn('id="feedback-panel" aria-labelledby="feedback-title" hidden', html)
                    self.assertIn("Filter Mission Control by project", html)
                    self.assertIn("No login, cloud service or telemetry", html)
                    self.assertNotIn("Agent brief", html)
                    self.assertNotIn("What matters now", html)
                    self.assertNotIn('id="agent-enabled"', html)
                body = json.dumps({"refresh_seconds": 300}).encode("utf-8")
                request = urllib.request.Request(
                    base + "/api/settings",
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    settings = json.load(response)
                    self.assertEqual(settings["refresh_seconds"], 300)
                with mock.patch.object(runtime, "start_doctor", return_value={"doctor": {"running": True}}) as start_doctor:
                    doctor_request = urllib.request.Request(
                        base + "/api/doctor",
                        data=b"{}",
                        method="POST",
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(doctor_request, timeout=5) as response:
                        self.assertEqual(response.status, HTTPStatus.ACCEPTED)
                        self.assertTrue(json.load(response)["doctor"]["running"])
                    start_doctor.assert_called_once_with()

                with mock.patch.object(runtime, "start_doctor") as start_doctor:
                    hostile = urllib.request.Request(
                        base + "/api/doctor",
                        data=b"{}",
                        method="POST",
                        headers={
                            "Content-Type": "application/json",
                            "Origin": "https://attacker.example",
                        },
                    )
                    with self.assertRaises(urllib.error.HTTPError) as raised:
                        urllib.request.urlopen(hostile, timeout=5)
                    self.assertEqual(raised.exception.code, HTTPStatus.FORBIDDEN)
                    start_doctor.assert_not_called()

                plain_text = urllib.request.Request(
                    base + "/api/refresh",
                    data=b"{}",
                    method="POST",
                    headers={"Content-Type": "text/plain"},
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(plain_text, timeout=5)
                self.assertEqual(raised.exception.code, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            finally:
                server.shutdown()
                server.server_close()
                runtime.stop()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
