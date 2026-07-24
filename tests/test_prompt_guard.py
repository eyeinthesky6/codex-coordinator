from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "codex-coordinator"
SCRIPT = PLUGIN / "scripts" / "codex_coordinator_prompt_guard.py"
COORDINATOR_ID = "11111111-2222-4333-8444-555555555555"
WORKER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
LANE_KEY = "focused-release-lane"


class PromptGuardTests(unittest.TestCase):
    def _repository(self, parent: Path, name: str) -> Path:
        root = parent / name
        root.mkdir()
        (root / ".git").mkdir()
        return root

    def _enable_coordinator(self, root: Path, project_id: str = "sample") -> str:
        marker = root / ".codex" / "coordination" / "project.yaml"
        marker.parent.mkdir(parents=True)
        marker.write_text(
            "\n".join(
                (
                    "schema_version: 2",
                    "coordination_enabled: true",
                    f"project_id: {project_id}",
                    "cross_project_task_access: false",
                    "cross_project_state_changes: false",
                    "active: .codex/coordination/active",
                    "archive: .codex/coordination/archive",
                    "",
                )
            ),
            encoding="utf-8",
        )
        created_at = "2026-07-24T00:00:00+00:00"
        active = marker.parent / "active"
        active.mkdir(exist_ok=True)
        (active / f"{COORDINATOR_ID}.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "projectId": project_id,
                    "threadId": COORDINATOR_ID,
                    "title": "Goal Coordinator",
                    "goal": "Coordinate the shared goal",
                    "status": "active",
                    "revision": 1,
                    "createdAt": created_at,
                    "updatedAt": created_at,
                    "paths": ["docs"],
                    "actions": ["goal-coordination"],
                    "blockedBy": [],
                    "limitOverride": False,
                }
            ),
            encoding="utf-8",
        )
        material = json.dumps(
            [project_id, COORDINATOR_ID, created_at, LANE_KEY],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return "ga-" + hashlib.sha256(material).hexdigest()[:32]

    def _communication(
        self,
        root: Path,
        *,
        kind: str = "GOAL_ASSIGNMENT",
        project_id: str = "sample",
        goal: str = "finish the work and pass its focused checks",
    ) -> str:
        assignment_id = self._enable_coordinator(root, project_id=project_id)
        sender = COORDINATOR_ID if kind == "GOAL_ASSIGNMENT" else WORKER_ID
        recipient = WORKER_ID if kind == "GOAL_ASSIGNMENT" else COORDINATOR_ID
        lines = [
            "Inter-agent task communication — no user action needed.",
            f"Project: {project_id}",
            f"Kind: {kind}",
            f"Assignment-ID: {assignment_id}",
            f"Lane-Key: {LANE_KEY}",
            f"Sender: {sender}",
            f"Recipient: {recipient}",
            f"Repository: {root}",
        ]
        if kind == "GOAL_ASSIGNMENT":
            lines.extend(("Native-Goal: REQUIRED", f"Goal: {goal}"))
        else:
            lines.append("Effect: terminal result is ready in the sender task")
        return "\n".join(lines)

    def _run(self, cwd: Path, prompt: str) -> tuple[int, str]:
        completed = subprocess.run(
            [sys.executable, "-I", str(SCRIPT)],
            input=json.dumps(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "turn_id": "turn-1",
                    "cwd": str(cwd),
                    "prompt": prompt,
                }
            ),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.stderr, "")
        return completed.returncode, completed.stdout

    def test_matching_repository_and_nested_cwd_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            nested = root / "src" / "service"
            nested.mkdir(parents=True)
            prompt = self._communication(root).replace(
                f"Repository: {root}", f"Repository: `{root}`"
            )
            code, output = self._run(nested, prompt)
            result = json.loads(output)
            self.assertEqual(code, 0)
            self.assertTrue(result["continue"])
            self.assertIn("call get_goal", result["systemMessage"])
            self.assertIn("call create_goal", result["systemMessage"])
            self.assertIn("Keep the native goal active", result["systemMessage"])

    def test_mismatched_repository_is_blocked_before_goal_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            current = self._repository(parent, "coordinator")
            requested = self._repository(parent, "product")
            code, output = self._run(current, self._communication(requested))
            result = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(result["decision"], "block")
        self.assertIn("Repository mismatch", result["reason"])
        self.assertIn(str(current.resolve()), result["reason"])
        self.assertIn(str(requested.resolve()), result["reason"])
        self.assertIn("Do not activate or execute the goal here", result["reason"])

    def test_delegation_envelope_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            current = self._repository(parent, "coordinator")
            requested = self._repository(parent, "product")
            communication = self._communication(requested)
            prompt = "\n".join(
                (
                    "<codex_delegation>",
                    f"<source_thread_id>{COORDINATOR_ID}</source_thread_id>",
                    f"<input>{communication}</input>",
                    "</codex_delegation>",
                )
            )
            _, output = self._run(current, prompt)
        self.assertEqual(json.loads(output)["decision"], "block")

    def test_documented_communication_shape_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            current = self._repository(parent, "coordinator")
            requested = self._repository(parent, "product")
            prompt = self._communication(requested)
            _, output = self._run(current, prompt)
        self.assertEqual(json.loads(output)["decision"], "block")

    def test_documented_communication_shape_allows_the_attached_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            prompt = self._communication(root)
            code, output = self._run(root, prompt)
            self.assertEqual(code, 0)
            self.assertIn("create_goal", json.loads(output)["systemMessage"])

    def test_goal_assignment_requires_native_goal_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            valid = self._communication(root, goal="finish the vertical")
            missing_marker = valid.replace("Native-Goal: REQUIRED\n", "")
            _, output = self._run(root, missing_marker)
            result = json.loads(output)
            self.assertEqual(result["decision"], "block")
            self.assertIn("Native-Goal: REQUIRED", result["reason"])

            missing_goal = valid.replace("Goal: finish the vertical", "")
            _, output = self._run(root, missing_goal)
            result = json.loads(output)
            self.assertEqual(result["decision"], "block")
            self.assertIn("non-empty Goal", result["reason"])

    def test_goal_marker_is_checked_beyond_eight_kilobytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            current = self._repository(parent, "coordinator")
            requested = self._repository(parent, "product")
            prompt = ("context " * 1_200) + "\n" + self._communication(requested)
            _, output = self._run(current, prompt)
        self.assertEqual(json.loads(output)["decision"], "block")

    def test_ordinary_repository_text_without_assignment_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            cases = (
                "Explain this example:\nRepository: C:\\example",
                "Compare these fields:\nKind: COLLISION\nRepository: owner/name",
            )
            for prompt in cases:
                with self.subTest(prompt=prompt):
                    self.assertEqual(self._run(root, prompt), (0, ""))

    def test_valid_released_communication_is_guarded_as_non_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            self._enable_coordinator(root)
            prompt = "\n".join(
                (
                    "Inter-agent task communication — no user action needed.",
                    "Project: sample",
                    "Kind: RELEASED",
                    "Sender: 11111111-2222-4333-8444-555555555555",
                    "Recipient: aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "Boundary: src/service.py exact writer hunk",
                    "Effect: Resolved: the earlier collision on this boundary no longer exists.",
                )
            )
            code, output = self._run(root, prompt)
            result = json.loads(output)

        self.assertEqual(code, 0)
        self.assertTrue(result["continue"])
        self.assertIn("non-executable", result["systemMessage"])
        self.assertIn("does not assign work", result["systemMessage"])
        self.assertIn("grant permission", result["systemMessage"])
        self.assertIn("existing goal and claim", result["systemMessage"])

    def test_legacy_task_boundary_header_is_rejected_with_neutral_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            self._enable_coordinator(root)
            prompt = "\n".join(
                (
                    "Internal task-boundary notice — no user action needed.",
                    "Project: sample",
                    "Kind: RELEASED",
                    "Sender: 11111111-2222-4333-8444-555555555555",
                    "Recipient: aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "Boundary: src/service.py exact writer hunk",
                    "Effect: Resolved: the earlier collision no longer exists.",
                )
            )
            _, output = self._run(root, prompt)
            result = json.loads(output)

        self.assertEqual(result["decision"], "block")
        self.assertIn("Inter-agent task communication", result["reason"])
        self.assertIn("no longer accepted", result["reason"])

    def test_inter_agent_communication_rejects_schema_and_revision_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            self._enable_coordinator(root, project_id="profitpilot")
            prompt = "\n".join(
                (
                    "Inter-agent task communication — no user action needed.",
                    "Project: profitpilot (schema 2)",
                    "Kind: RELEASED",
                    "Sender: 11111111-2222-4333-8444-555555555555 (active claim revision 8)",
                    "Recipient: aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee (active claim revision 1)",
                    "Boundary: src/service.py exact writer hunk",
                    "Effect: You may now edit this hunk. Production remains held.",
                )
            )
            _, output = self._run(root, prompt)
            result = json.loads(output)

        self.assertEqual(result["decision"], "block")
        self.assertIn("plain Project ID", result["reason"])
        self.assertIn("Do not append schema versions", result["reason"])

    def test_inter_agent_communication_cannot_grant_permission_or_relay_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            self._enable_coordinator(root)
            prompt = "\n".join(
                (
                    "Inter-agent task communication — no user action needed.",
                    "Project: sample",
                    "Kind: RELEASED",
                    "Sender: 11111111-2222-4333-8444-555555555555",
                    "Recipient: aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "Boundary: src/service.py exact writer hunk",
                    "Effect: You may now edit this hunk. Production remains held.",
                )
            )
            _, output = self._run(root, prompt)
            result = json.loads(output)

        self.assertEqual(result["decision"], "block")
        self.assertIn("Start Effect with `Resolved:`", result["reason"])
        self.assertIn("Do not grant permission", result["reason"])

    def test_inter_agent_communication_must_match_enabled_local_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            self._enable_coordinator(root, project_id="sample")
            prompt = "\n".join(
                (
                    "Inter-agent task communication — no user action needed.",
                    "Project: another-project",
                    "Kind: DEPENDENCY",
                    "Sender: 11111111-2222-4333-8444-555555555555",
                    "Recipient: aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "Boundary: src/service.py exact writer hunk",
                    "Effect: Blocked: this result needs that exact hunk to be released.",
                )
            )
            _, output = self._run(root, prompt)
            result = json.loads(output)

        self.assertEqual(result["decision"], "block")
        self.assertIn("Project mismatch", result["reason"])
        self.assertIn("another-project", result["reason"])

    def test_inter_agent_communication_does_not_accept_assignment_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            self._enable_coordinator(root)
            prompt = "\n".join(
                (
                    "Inter-agent task communication — no user action needed.",
                    "Project: sample",
                    "Kind: COLLISION",
                    "Sender: 11111111-2222-4333-8444-555555555555",
                    "Recipient: aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "Assignment-ID: ga-0123456789abcdef0123456789abcdef",
                    f"Repository: {root}",
                    "Boundary: src/service.py exact writer hunk",
                    "Effect: Paused: both tasks reached the same incompatible hunk.",
                )
            )
            _, output = self._run(root, prompt)
            result = json.loads(output)

        self.assertEqual(result["decision"], "block")
        self.assertIn("do not carry assignment authority", result["reason"])
        self.assertIn("Assignment-ID", result["reason"])
        self.assertIn("Repository", result["reason"])

    def test_assignment_requires_one_absolute_local_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            valid = self._communication(root)
            cases = (
                "\n".join(
                    line for line in valid.splitlines() if not line.startswith("Repository:")
                ),
                valid.replace(f"Repository: {root}", "Repository: owner/name"),
            )
            for prompt in cases:
                with self.subTest(prompt=prompt):
                    _, output = self._run(root, prompt)
                    result = json.loads(output)
                    self.assertEqual(result["decision"], "block")
                    self.assertIn("absolute local Repository", result["reason"])

    def test_assignment_rejects_duplicate_repository_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            prompt = self._communication(root).replace(
                f"Repository: {root}",
                f"Repository: {root}\nRepository: {root}",
            )
            _, output = self._run(root, prompt)
            result = json.loads(output)

            self.assertEqual(result["decision"], "block")
            self.assertIn("exactly one Repository line", result["reason"])

    def test_unverifiable_absolute_repository_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = self._repository(parent, "product")
            missing = parent / "missing"
            _, output = self._run(
                root,
                self._communication(root).replace(
                    f"Repository: {root}", f"Repository: {missing}"
                ),
            )
        result = json.loads(output)
        self.assertEqual(result["decision"], "block")
        self.assertIn("could not verify", result["reason"])

    def test_assignment_requires_one_valid_assignment_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            valid = self._communication(root)
            valid_id = next(
                line.split(":", 1)[1].strip()
                for line in valid.splitlines()
                if line.startswith("Assignment-ID:")
            )
            cases = (
                "\n".join(
                    line for line in valid.splitlines() if not line.startswith("Assignment-ID:")
                ),
                valid.replace(valid_id, "invalid"),
                valid.replace(
                    f"Assignment-ID: {valid_id}",
                    f"Assignment-ID: {valid_id}\nAssignment-ID: {valid_id}",
                ),
            )
            for prompt in cases:
                with self.subTest(prompt=prompt):
                    _, output = self._run(root, prompt)
                    result = json.loads(output)
                    self.assertEqual(result["decision"], "block")
                    self.assertIn("Assignment-ID", result["reason"])

    def test_result_ready_uses_the_same_repository_and_assignment_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            current = self._repository(parent, "product")
            other = self._repository(parent, "other")
            matching = self._communication(current, kind="RESULT_READY")
            self.assertEqual(self._run(current, matching), (0, ""))
            mismatched = matching.replace(str(current), str(other))
            _, output = self._run(current, mismatched)
            self.assertIn("Repository mismatch", json.loads(output)["reason"])

    def test_well_formed_but_fabricated_assignment_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(Path(directory), "product")
            prompt = self._communication(root)
            actual = next(
                line.split(":", 1)[1].strip()
                for line in prompt.splitlines()
                if line.startswith("Assignment-ID:")
            )
            fabricated = "ga-0123456789abcdef0123456789abcdef"
            self.assertNotEqual(actual, fabricated)
            _, output = self._run(root, prompt.replace(actual, fabricated))
            result = json.loads(output)

        self.assertEqual(result["decision"], "block")
        self.assertIn("provenance mismatch", result["reason"])
        self.assertIn("well-formed", result["reason"])

    def test_invalid_hook_input_is_quiet(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", str(SCRIPT)],
            input="not json",
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
