from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

try:
    from hypothesis import HealthCheck, settings, strategies as st
    from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule
except ModuleNotFoundError as error:  # Keep the dependency-free default suite usable.
    raise unittest.SkipTest(
        "install requirements-property-tests.txt to run handover properties"
    ) from error


REPOSITORY = Path(__file__).resolve().parents[1]
HELPER = (
    REPOSITORY
    / "plugins"
    / "codex-coordinator"
    / "skills"
    / "codex-coordinator"
    / "scripts"
    / "coordination_state.py"
)
SPEC = importlib.util.spec_from_file_location("coordination_state_properties", HELPER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load coordination state helper")
state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state)


COORDINATORS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
)


class InboxHandoverMachine(RuleBasedStateMachine):
    """Exercise replacement and interrupted-handoff sequences against the real helper."""

    def __init__(self) -> None:
        super().__init__()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / ".codex" / "coordination"
        self.project_id = "property-project"
        self.epoch = 1
        self.coordinator = COORDINATORS[0]
        self.records: dict[str, bytes] = {}
        self.next_record = 0

    def teardown(self) -> None:
        self.temporary.cleanup()

    def scan(self) -> dict[str, object]:
        return state.scan_inbox(
            self.root,
            project_id=self.project_id,
            coordination_epoch=self.epoch,
            coordinator_id=self.coordinator,
        )

    def acknowledge_everything(self) -> None:
        report = self.scan()
        pending = {
            Path(record["path"]).name: record["sha256"]
            for record in report["pendingRecords"]
        }
        if pending:
            state.acknowledge_inbox(
                self.root,
                project_id=self.project_id,
                coordination_epoch=self.epoch,
                coordinator_id=self.coordinator,
                records=pending,
            )
        self.assert_clean_for_current_owner()

    def assert_clean_for_current_owner(self) -> None:
        report = self.scan()
        assert report["pendingRecords"] == []

    @rule(payload=st.binary(min_size=0, max_size=128))
    def create_record(self, payload: bytes) -> None:
        name = f"handover-{self.next_record:04d}.md"
        self.next_record += 1
        state.create_file(self.root, Path("inbox") / name, payload)
        self.records[name] = payload
        pending = {
            Path(record["path"]).name for record in self.scan()["pendingRecords"]
        }
        assert name in pending

    @precondition(lambda self: bool(self.records))
    @rule()
    def acknowledge_then_replace_coordinator(self) -> None:
        self.acknowledge_everything()
        self.coordinator = (
            COORDINATORS[1]
            if self.coordinator == COORDINATORS[0]
            else COORDINATORS[0]
        )
        report = self.scan()
        assert report["cacheStatus"] == "scope_changed"
        assert {
            Path(record["path"]).name for record in report["pendingRecords"]
        } == set(self.records)

    @precondition(lambda self: bool(self.records))
    @rule()
    def acknowledge_then_advance_epoch(self) -> None:
        self.acknowledge_everything()
        self.epoch += 1
        report = self.scan()
        assert report["cacheStatus"] == "scope_changed"
        assert {
            Path(record["path"]).name for record in report["pendingRecords"]
        } == set(self.records)

    @precondition(lambda self: bool(self.records))
    @rule(payload=st.binary(min_size=0, max_size=128))
    def acknowledged_record_change_becomes_pending(self, payload: bytes) -> None:
        self.acknowledge_everything()
        name = sorted(self.records)[0]
        changed = self.records[name] + payload + b"changed"
        (self.root / "inbox" / name).write_bytes(changed)
        self.records[name] = changed
        report = self.scan()
        pending = {
            Path(record["path"]).name: record
            for record in report["pendingRecords"]
        }
        assert pending[name]["reason"] == "changed"

    @precondition(lambda self: bool(self.records))
    @rule()
    def repeated_acknowledgement_is_stable(self) -> None:
        self.acknowledge_everything()
        self.acknowledge_everything()

    @invariant()
    def pending_hashes_always_match_disk(self) -> None:
        for record in self.scan()["pendingRecords"]:
            content = (self.root / "inbox" / Path(record["path"]).name).read_bytes()
            assert record["sha256"] == hashlib.sha256(content).hexdigest()


TestInboxHandoverProperties = InboxHandoverMachine.TestCase
TestInboxHandoverProperties.settings = settings(
    max_examples=100,
    stateful_step_count=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


if __name__ == "__main__":
    unittest.main()
