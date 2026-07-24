from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
STATE_TOOL = (
    REPOSITORY
    / "plugins"
    / "codex-coordinator"
    / "skills"
    / "codex-coordinator"
    / "scripts"
    / "coordination_state.py"
)
SPEC = importlib.util.spec_from_file_location("fault_protocol_state", STATE_TOOL)
assert SPEC and SPEC.loader
state = importlib.util.module_from_spec(SPEC)
sys.dont_write_bytecode = True
SPEC.loader.exec_module(state)


COORDINATOR = "11111111-2222-4333-8444-555555555555"
WORKER = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class ResponseLost(RuntimeError):
    """The fake host committed the mutation but lost its result."""


class FakeNativeHost:
    def __init__(self) -> None:
        self.tasks: list[str] = []
        self.messages: list[str] = []
        self.create_calls = 0
        self.send_calls = 0

    def create_task_then_lose_response(self, assignment_id: str) -> None:
        self.create_calls += 1
        self.tasks.append(assignment_id)
        raise ResponseLost("No handler registered")

    def send_result_then_lose_response(self, assignment_id: str) -> None:
        self.send_calls += 1
        self.messages.append(assignment_id)
        raise ResponseLost("No handler registered")


def _project(directory: str) -> Path:
    root = Path(directory)
    marker = root / ".codex" / "coordination" / "project.yaml"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        "\n".join(
            (
                "schema_version: 2",
                "coordination_enabled: true",
                "project_id: sample",
                "canonical_paths:",
                "  active: .codex/coordination/active",
                "  archive: .codex/coordination/archive",
                "access:",
                "  cross_project_task_access: false",
                "  cross_project_state_changes: false",
                "",
            )
        ),
        encoding="utf-8",
    )
    state.claim_boundary(
        root,
        thread_id=COORDINATOR,
        title="Coordinate one goal",
        goal="Finish one bounded shared goal",
        paths=[],
        actions=["goal-coordination"],
        blocked_by=[],
        status="active",
        expected_revision=0,
        user_approved_over_limit=False,
    )
    return root


class NativeTaskFaultProtocolTests(unittest.TestCase):
    def test_committed_create_with_lost_response_is_used_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            identity = state.assignment_identity(
                root,
                coordinator_thread_id=COORDINATOR,
                lane_key="runtime-owner",
            )["assignmentId"]
            host = FakeNativeHost()

            preflight = state.reconcile_assignment_receipt(
                assignment_id=identity,
                observed_assignment_ids=host.tasks,
                outcome="not-attempted",
            )
            self.assertEqual(preflight["decision"], "safe-to-attempt")
            with self.assertRaises(ResponseLost):
                host.create_task_then_lose_response(identity)
            readback = state.reconcile_assignment_receipt(
                assignment_id=identity,
                observed_assignment_ids=host.tasks,
                outcome="ambiguous",
            )
            pending_root = root / ".codex" / "coordination" / "pending-notices"
            pending_root_exists = pending_root.exists()

        self.assertEqual(readback["decision"], "use-existing")
        self.assertEqual(host.create_calls, 1)
        self.assertEqual(host.tasks, [identity])
        self.assertFalse(pending_root_exists)

    def test_committed_result_ready_with_lost_response_is_not_resent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            identity = state.assignment_identity(
                _project(directory),
                coordinator_thread_id=COORDINATOR,
                lane_key="runtime-owner",
            )["assignmentId"]
            host = FakeNativeHost()

            with self.assertRaises(ResponseLost):
                host.send_result_then_lose_response(identity)
            readback = state.reconcile_assignment_receipt(
                assignment_id=identity,
                observed_assignment_ids=host.messages,
                outcome="ambiguous",
            )

        self.assertEqual(readback["decision"], "use-existing")
        self.assertEqual(host.send_calls, 1)
        self.assertEqual(host.messages, [identity])

    def test_ambiguous_mutation_without_a_visible_receipt_records_one_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _project(directory)
            identity = state.assignment_identity(
                root,
                coordinator_thread_id=COORDINATOR,
                lane_key="runtime-owner",
            )["assignmentId"]
            report = state.reconcile_assignment_receipt(
                assignment_id=identity,
                observed_assignment_ids=[],
                outcome="ambiguous",
            )
            created = state.create_pending_notice(
                root,
                assignment_id=identity,
                kind="GOAL_ASSIGNMENT",
                sender_thread_id=COORDINATOR,
                recipient_thread_id=WORKER,
            )
            repeated = state.create_pending_notice(
                root,
                assignment_id=identity,
                kind="GOAL_ASSIGNMENT",
                sender_thread_id=COORDINATOR,
                recipient_thread_id=WORKER,
            )
            pending = state.list_pending_notices(
                root, recipient_thread_id=WORKER
            )

        self.assertEqual(report["decision"], "stop-unknown")
        self.assertEqual(created["status"], "created")
        self.assertEqual(repeated["status"], "existing")
        self.assertEqual(pending["pendingCount"], 1)


if __name__ == "__main__":
    unittest.main()
