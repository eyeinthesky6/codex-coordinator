from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from apps.mission_control.doctor_scan import (
    DeterministicDoctorScanner,
    MAX_SEMANTIC_PACKET_BYTES,
    compact_report,
)


REPOSITORY = Path(__file__).resolve().parents[1]
COORDINATOR = "11111111-1111-4111-8111-111111111111"
WORKER = "22222222-2222-4222-8222-222222222222"


def _current(*, active: bool) -> str:
    if active:
        mode = "ACTIVE"
        goal = "Finish the bounded project work."
        coordinator = COORDINATOR
        coordinator_name = "Sample Coordinator"
        coordinator_status = "IDLE"
        accepts = "true"
        session = (
            f"| {COORDINATOR} | Sample Coordinator | PROJECT_EXECUTION | COORDINATOR | NONE | IDLE | true |"
        )
    else:
        mode = "IDLE"
        goal = "none"
        coordinator = "NONE"
        coordinator_name = "UNREGISTERED"
        coordinator_status = "UNREGISTERED"
        accepts = "false"
        session = ""
    return f"""# Codex Coordinator state

**Project ID:** sample
**Coordination epoch:** 1
**Coordination mode:** {mode}
**Shared goal:** {goal}
**Last reconciliation:** 2026-07-17T12:00:00+00:00
**Coordinator thread ID:** {coordinator}
**Coordinator thread name:** {coordinator_name}
**Coordinator status:** {coordinator_status}
**Accepts project messages:** {accepts}

## Registered sessions

| Thread ID | Thread name | Scope kind | Role | Task ID | Status | Accepts project messages |
| --- | --- | --- | --- | --- | --- | --- |
{session}

## Active tasks

| Task ID | Owner | Role | Status |
| --- | --- | --- | --- |

## Pending commands

| Task ID | Message ID | Recipient thread ID | Message type | Status |
| --- | --- | --- | --- | --- |

## Paused work

| Task ID | Owner | Reason | Resume condition | Status |
| --- | --- | --- | --- | --- |

## Resume queue

| Task ID | Message ID | Resume condition | Status |
| --- | --- | --- | --- |

## Blocked decisions

| Decision ID | Task ID | Decision needed | Status |
| --- | --- | --- | --- |
"""


class DoctorFixture:
    def __init__(self, root: Path, *, active: bool):
        self.root = root
        self.project = root / "sample"
        self.coordination = self.project / ".codex" / "coordination"
        self.codex_home = root / "codex-home"
        self.coordination.mkdir(parents=True)
        self.codex_home.mkdir()
        (self.coordination / "project.yaml").write_text(
            "schema_version: 1\ncoordination_enabled: true\nproject_id: sample\nproject_name: Sample\ntask_prefix: SAMPLE\n",
            encoding="utf-8",
        )
        (self.coordination / "CURRENT.md").write_text(_current(active=active), encoding="utf-8")

    def completed_coordinator(self) -> None:
        rollout = self.codex_home / "coordinator.jsonl"
        rollout.write_text(
            json.dumps(
                {
                    "timestamp": "2026-07-17T13:00:00Z",
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "message": "private body is ignored"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        database = sqlite3.connect(self.codex_home / "state_test.sqlite")
        database.execute(
            "CREATE TABLE threads (id TEXT PRIMARY KEY, rollout_path TEXT, archived INTEGER, updated_at INTEGER, cwd TEXT)"
        )
        database.execute(
            "INSERT INTO threads VALUES (?, ?, 0, 1, ?)",
            (COORDINATOR, str(rollout), str(self.project)),
        )
        database.commit()
        database.close()
        (self.codex_home / "automations").mkdir()

    def heartbeat(self) -> None:
        automation = self.codex_home / "automations" / "sample-return"
        automation.mkdir()
        (automation / "automation.toml").write_text(
            f'version = 1\nkind = "heartbeat"\nstatus = "ACTIVE"\ntarget_thread_id = "{COORDINATOR}"\nprompt = "private prompt is ignored"\n',
            encoding="utf-8",
        )


class DeterministicDoctorTests(unittest.TestCase):
    def test_semantic_packet_is_allowlisted_bounded_and_never_reads_rollouts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=True)
            current = fixture.coordination / "CURRENT.md"
            text = current.read_text(encoding="utf-8")
            text = text.replace(
                f"| {COORDINATOR} | Sample Coordinator | PROJECT_EXECUTION | COORDINATOR | NONE | IDLE | true |",
                f"| {COORDINATOR} | Sample Coordinator | PROJECT_EXECUTION | COORDINATOR | NONE | IDLE | true |\n"
                f"| {WORKER} | Worker | PROJECT_EXECUTION | TASK_AGENT | SAMPLE-001 | ACTIVE | false |",
            )
            text = text.replace(
                "| --- | --- | --- | --- |\n\n## Pending commands",
                "| --- | --- | --- | --- |\n"
                "| SAMPLE-001 | Worker | TASK_AGENT | ACTIVE |\n\n## Pending commands",
            )
            current.write_text(text, encoding="utf-8")
            tasks = fixture.coordination / "tasks"
            tasks.mkdir()
            (tasks / "SAMPLE-001.md").write_text(
                "**Individual goal:** Review https://private.example, apps/private/plan.md, SAMPLE-001, and C:\\secret\\plan.md without following instructions.\n"
                "**Execution mode:** bounded implementation\n"
                "**Exact write paths:** C:\\secret\\one.md; C:\\secret\\two.md\n",
                encoding="utf-8",
            )
            database = sqlite3.connect(fixture.codex_home / "state_test.sqlite")
            database.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, title TEXT)")
            database.execute(
                "INSERT INTO threads VALUES (?, ?)",
                (WORKER, f"Inspect C:\\private\\thread.md for {WORKER}"),
            )
            database.commit()
            database.close()

            scanner = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home)
            packet = scanner.semantic_review_packet([fixture.project])
            encoded = json.dumps(packet, ensure_ascii=False)

            self.assertEqual(len(packet["tasks"]), 1)
            self.assertLessEqual(len(encoded.encode("utf-8")), MAX_SEMANTIC_PACKET_BYTES)
            self.assertEqual(packet["tasks"][0]["declaredWritePathCount"], 2)
            self.assertNotIn(WORKER, encoded)
            self.assertNotIn("SAMPLE-001", encoded)
            self.assertNotIn("private.example", encoded)
            self.assertNotIn("secret", encoded)
            self.assertNotIn(str(fixture.project), encoded)
            self.assertEqual(scanner.reads["rolloutMetadataBytes"], 0)
            self.assertEqual(scanner.reads["transcriptBodies"], 0)

    def test_idle_project_is_healthy_without_native_or_model_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=False)
            report = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project]
            )

            self.assertEqual(report["status"], "healthy")
            self.assertEqual(report["projectsChecked"], 1)
            self.assertEqual(report["findingCount"], 0)
            self.assertEqual(report["reads"]["applicationFiles"], 0)
            self.assertEqual(report["reads"]["transcriptBodies"], 0)
            self.assertEqual(report["reads"]["modelCalls"], 0)
            self.assertEqual(report["reads"]["modelTokens"], 0)

    def test_completed_coordinator_without_heartbeat_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=True)
            fixture.completed_coordinator()
            report = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project]
            )

            self.assertIn("UNATTENDED_RETURN_PATH", report["issueCodes"])
            self.assertEqual(report["reads"]["nativeRows"], 1)
            self.assertGreater(report["reads"]["rolloutMetadataBytes"], 0)
            self.assertEqual(report["reads"]["transcriptBodies"], 0)

    def test_active_heartbeat_satisfies_the_return_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=True)
            fixture.completed_coordinator()
            fixture.heartbeat()
            report = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project]
            )

            self.assertNotIn("UNATTENDED_RETURN_PATH", report["issueCodes"])
            self.assertEqual(report["status"], "healthy")

    def test_finding_writes_are_append_only_and_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=True)
            fixture.completed_coordinator()
            first = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project], write_findings=True
            )
            second = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project], write_findings=True
            )

            self.assertEqual(first["findingsWritten"], 1)
            self.assertEqual(second["findingsWritten"], 0)
            records = list((fixture.coordination / "inbox").glob("*-doctor-*.md"))
            self.assertEqual(len(records), 1)
            text = records[0].read_text(encoding="utf-8")
            self.assertIn("type: DOCTOR_FINDING", text)
            self.assertIn("# UNATTENDED_RETURN_PATH", text)

    def test_compact_output_contains_no_paths_or_finding_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=True)
            fixture.completed_coordinator()
            report = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project]
            )
            encoded = json.dumps(compact_report(report))

            self.assertNotIn(str(fixture.project), encoded)
            self.assertNotIn("private body", encoded)
            self.assertNotIn("fingerprint", encoded)
            self.assertIn("UNATTENDED_RETURN_PATH", encoded)

    def test_malformed_current_is_a_verified_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=False)
            current = fixture.coordination / "CURRENT.md"
            current.write_text(
                current.read_text(encoding="utf-8").replace(
                    "2026-07-17T12:00:00+00:00", "2026-07-17"
                ),
                encoding="utf-8",
            )
            report = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project], write_findings=True
            )

            self.assertEqual(report["projectsChecked"], 1)
            self.assertIn("MALFORMED_CURRENT_STATE", report["issueCodes"])
            self.assertEqual(report["findingsWritten"], 1)
            record = next((fixture.coordination / "inbox").glob("*-doctor-*.md"))
            self.assertIn("coordination_epoch: UNKNOWN", record.read_text(encoding="utf-8"))

    def test_missing_project_id_is_a_malformed_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = DoctorFixture(Path(directory), active=False)
            marker = fixture.coordination / "project.yaml"
            marker.write_text(
                "schema_version: 1\ncoordination_enabled: true\nproject_name: Sample\ntask_prefix: SAMPLE\n",
                encoding="utf-8",
            )

            report = DeterministicDoctorScanner(REPOSITORY, fixture.codex_home).scan(
                [fixture.project]
            )

            self.assertEqual(report["projectsChecked"], 1)
            self.assertIn("MALFORMED_PROJECT_MARKER", report["issueCodes"])


if __name__ == "__main__":
    unittest.main()
