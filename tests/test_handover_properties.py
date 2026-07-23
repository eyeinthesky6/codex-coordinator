from __future__ import annotations

import importlib.util
import sys
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
sys.dont_write_bytecode = True
SPEC.loader.exec_module(state)


THREADS = tuple(
    f"{index:08x}-1111-4111-8111-{index:012x}" for index in range(1, 4)
)
TOKEN = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12)
FINAL_STATUS = st.sampled_from(
    ("completed", "stopped", "superseded", "stale-owner-confirmed")
)


def _project(directory: str) -> Path:
    root = Path(directory)
    marker = root / ".codex" / "coordination" / "project.yaml"
    marker.parent.mkdir(parents=True)
    marker.write_text(
        "\n".join(
            (
                "schema_version: 2",
                "coordination_enabled: true",
                "project_id: property-project",
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
    return root


class ClaimLifecycleMachine(RuleBasedStateMachine):
    """Exercise schema-2 claims and the derived CURRENT view through real APIs."""

    def __init__(self) -> None:
        super().__init__()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = _project(self.temporary.name)
        self.active: dict[int, dict[str, object]] = {}
        self.current_generated = False

    def teardown(self) -> None:
        self.temporary.cleanup()

    @property
    def current(self) -> Path:
        return self.root / ".codex" / "coordination" / "CURRENT.md"

    def _ownership(self, index: int, revision: int) -> tuple[list[str], list[str]]:
        if index == 0:
            return [], ["goal-coordination", "git-integration"]
        return [f"lanes/{index}/v{revision}"], []

    def _write_claim(
        self,
        index: int,
        *,
        token: str,
        status: str,
    ) -> dict[str, object]:
        existing = self.active.get(index)
        expected_revision = int(existing["revision"]) if existing else 0
        revision = expected_revision + 1
        paths, actions = self._ownership(index, revision)
        title = f"Lane {index} {token}"
        goal = f"Complete vertical {index} {token}"
        result = state.claim_boundary(
            self.root,
            thread_id=THREADS[index],
            title=title,
            goal=goal,
            paths=paths,
            actions=actions,
            blocked_by=[],
            status=status,
            expected_revision=expected_revision,
            user_approved_over_limit=False,
        )
        record = result["record"]
        assert record["revision"] == revision
        self.active[index] = {
            "revision": revision,
            "title": title,
            "goal": goal,
            "paths": paths,
            "actions": actions,
            "status": status,
        }
        self.current_generated = True
        return result

    @precondition(lambda self: len(self.active) < len(THREADS))
    @rule(selector=st.integers(min_value=0, max_value=2), token=TOKEN)
    def claim_disjoint_lane(self, selector: int, token: str) -> None:
        available = [index for index in range(len(THREADS)) if index not in self.active]
        index = available[selector % len(available)]
        result = self._write_claim(index, token=token, status="active")
        assert result["status"] == "claimed"

    @precondition(lambda self: bool(self.active))
    @rule(
        selector=st.integers(min_value=0, max_value=2),
        token=TOKEN,
        blocked=st.booleans(),
    )
    def update_exact_owner(
        self, selector: int, token: str, blocked: bool
    ) -> None:
        indices = sorted(self.active)
        index = indices[selector % len(indices)]
        result = self._write_claim(
            index,
            token=token,
            status="blocked" if blocked else "active",
        )
        assert result["status"] == "updated"

    @precondition(lambda self: bool(self.active))
    @rule(selector=st.integers(min_value=0, max_value=2), token=TOKEN)
    def stale_revision_cannot_change_claim_or_view(
        self, selector: int, token: str
    ) -> None:
        indices = sorted(self.active)
        index = indices[selector % len(indices)]
        record = self.active[index]
        claim_path = (
            self.root
            / ".codex"
            / "coordination"
            / "active"
            / f"{THREADS[index]}.json"
        )
        claim_before = claim_path.read_bytes()
        current_before = self.current.read_bytes()
        paths, actions = self._ownership(index, int(record["revision"]) + 1)
        try:
            state.claim_boundary(
                self.root,
                thread_id=THREADS[index],
                title=f"Rejected {token}",
                goal=f"Rejected stale update {token}",
                paths=paths,
                actions=actions,
                blocked_by=[],
                status="active",
                expected_revision=int(record["revision"]) + 1,
                user_approved_over_limit=False,
            )
        except state.BoardError as error:
            assert "revision changed" in str(error)
        else:
            raise AssertionError("a stale revision changed an active claim")
        assert claim_path.read_bytes() == claim_before
        assert self.current.read_bytes() == current_before

    @precondition(
        lambda self: bool(self.active) and len(self.active) < len(THREADS)
    )
    @rule(
        active_selector=st.integers(min_value=0, max_value=2),
        free_selector=st.integers(min_value=0, max_value=2),
        token=TOKEN,
    )
    def overlapping_claim_cannot_change_board_or_view(
        self, active_selector: int, free_selector: int, token: str
    ) -> None:
        active_indices = sorted(self.active)
        free_indices = [index for index in range(len(THREADS)) if index not in self.active]
        owner_index = active_indices[active_selector % len(active_indices)]
        candidate_index = free_indices[free_selector % len(free_indices)]
        owner = self.active[owner_index]
        paths = list(owner["paths"])
        actions = [] if paths else [str(owner["actions"][0])]
        board_before = state.list_board(self.root)
        current_before = self.current.read_bytes()
        try:
            state.claim_boundary(
                self.root,
                thread_id=THREADS[candidate_index],
                title=f"Conflicting lane {token}",
                goal=f"Conflicting vertical {token}",
                paths=paths,
                actions=actions,
                blocked_by=[],
                status="active",
                expected_revision=0,
                user_approved_over_limit=False,
            )
        except state.ClaimConflict:
            pass
        else:
            raise AssertionError("an overlapping claim was accepted")
        assert state.list_board(self.root) == board_before
        assert self.current.read_bytes() == current_before

    @precondition(lambda self: bool(self.active))
    @rule(selector=st.integers(min_value=0, max_value=2), token=TOKEN)
    def stale_current_is_rebuilt_from_claims(
        self, selector: int, token: str
    ) -> None:
        self.current.write_text("STALE_PRIVATE_HISTORY\n", encoding="utf-8")
        indices = sorted(self.active)
        index = indices[selector % len(indices)]
        self._write_claim(index, token=token, status=str(self.active[index]["status"]))
        assert "STALE_PRIVATE_HISTORY" not in self.current.read_text(encoding="utf-8")

    @precondition(lambda self: bool(self.active))
    @rule(
        selector=st.integers(min_value=0, max_value=2),
        final_status=FINAL_STATUS,
    )
    def release_exact_owner(self, selector: int, final_status: str) -> None:
        indices = sorted(self.active)
        index = indices[selector % len(indices)]
        revision = int(self.active[index]["revision"])
        result = state.release_boundary(
            self.root,
            thread_id=THREADS[index],
            expected_revision=revision,
            final_status=final_status,
        )
        receipt = result["receipt"]
        assert result["status"] == "released"
        assert receipt["lastRevision"] == revision
        assert receipt["finalStatus"] == final_status
        assert "paths" not in receipt
        assert "actions" not in receipt
        self.active.pop(index)
        self.current_generated = True

    @rule()
    def read_only_observation_never_creates_authority(self) -> None:
        before = dict(self.active)
        report = state.list_board(self.root)
        assert report["activeCount"] == len(before)
        assert self.active == before

    @invariant()
    def canonical_board_and_current_view_match_model(self) -> None:
        report = state.list_board(self.root)
        assert report["status"] == "ok"
        assert report["activeCount"] == len(self.active)
        assert report["conflicts"] == []
        records = {record["threadId"]: record for record in report["records"]}
        assert set(records) == {THREADS[index] for index in self.active}

        for index, expected in self.active.items():
            record = records[THREADS[index]]
            for field in ("revision", "title", "goal", "paths", "actions", "status"):
                assert record[field] == expected[field]
            claim_path = (
                self.root
                / ".codex"
                / "coordination"
                / "active"
                / f"{THREADS[index]}.json"
            )
            assert claim_path.stat().st_size <= state.MAX_RECORD_BYTES

        if not self.current_generated:
            assert not self.current.exists()
            return

        current = self.current.read_text(encoding="utf-8")
        assert "Generated active-only view" in current
        assert f"Active lanes: {len(self.active)}" in current
        for index, expected in self.active.items():
            assert THREADS[index] in current
            assert str(expected["title"]) in current
            assert str(expected["goal"]) in current
            assert str(expected["status"]) in current
            for path in expected["paths"]:
                assert f"path: {path}" in current
            for action in expected["actions"]:
                assert f"action: {action}" in current
        for index in range(len(THREADS)):
            if index not in self.active:
                assert THREADS[index] not in current
        for private_field in ("createdAt", "updatedAt", "revision", "closedAt"):
            assert private_field not in current
        if 0 in self.active:
            assert current.count("Coordinator:") == 1
            assert current.count("Shared goal:") == 1
            assert current.count("Git integration owner:") == 1
        else:
            assert "Coordinator:" not in current
            assert "Shared goal:" not in current
            assert "Git integration owner:" not in current


TestClaimLifecycleProperties = ClaimLifecycleMachine.TestCase
TestClaimLifecycleProperties.settings = settings(
    max_examples=100,
    stateful_step_count=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


if __name__ == "__main__":
    unittest.main()
