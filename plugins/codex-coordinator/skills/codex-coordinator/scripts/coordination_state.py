#!/usr/bin/env python3
"""Read and update the local Codex task-boundary board.

The board stores one small JSON claim per active Codex task and generates a
human-readable active view from those claims. A failed native assignment or
terminal return may also leave one routing-only pending delivery record until delivery
or recipient action is verified. It never reads or stores task
transcripts, prompts, reasoning, tool output, results, or full-turn logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


MARKER_SCHEMA_VERSION = 2
CLAIM_SCHEMA_VERSION = 1
DEFAULT_ACTIVE_TASK_CEILING = 5
MAX_RECORD_BYTES = 4096
MAX_PATHS = 32
MAX_ACTIONS = 16
MAX_DEPENDENCIES = 16
MAX_PENDING_NOTICES_PER_RECIPIENT = 32
CURRENT_VIEW_NAME = "CURRENT.md"
PENDING_NOTICE_DIRECTORY = "pending-notices"
LEGACY_ADVISORY_ACTIONS = frozenset({"git-integration"})

PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
THREAD_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
ACTION = re.compile(r"[a-z][a-z0-9-]{0,63}")
LANE_KEY = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
ASSIGNMENT_ID = re.compile(r"ga-[0-9a-f]{32}")
NOTICE_ID = re.compile(r"pn-[0-9a-f]{32}")
NOTICE_KINDS = frozenset({"GOAL_ASSIGNMENT", "RESULT_READY"})
CLAIM_KEYS = {
    "schemaVersion",
    "projectId",
    "threadId",
    "title",
    "goal",
    "status",
    "revision",
    "createdAt",
    "updatedAt",
    "paths",
    "actions",
    "blockedBy",
    "limitOverride",
}
PENDING_NOTICE_KEYS = {
    "schemaVersion",
    "noticeId",
    "projectId",
    "assignmentId",
    "kind",
    "senderThreadId",
    "recipientThreadId",
    "repository",
    "deliveryState",
    "createdAt",
}


class BoardError(RuntimeError):
    """Raised when board state is invalid or a requested write is unsafe."""


class ClaimConflict(BoardError):
    """Raised when a proposed claim overlaps an exclusive active action."""

    def __init__(self, conflicts: list[dict[str, Any]]):
        super().__init__("The requested exclusive action overlaps an active task claim")
        self.conflicts = conflicts


def _is_linklike(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.exists() and path.is_junction()
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise BoardError(f"Duplicate JSON key: {key}")
        value[key] = child
    return value


def _read_json(path: Path, *, maximum: int = MAX_RECORD_BYTES) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise BoardError(f"Cannot read board record {path.name}: {error}") from error
    if len(raw) > maximum:
        raise BoardError(f"Board record exceeds {maximum} bytes: {path.name}")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BoardError(f"Cannot parse board record {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise BoardError(f"Board record is not a JSON object: {path.name}")
    return value


def _marker_value(text: str, key: str) -> str:
    matches = re.findall(
        rf"(?mi)^\s*{re.escape(key)}\s*:\s*([^#\r\n]+?)\s*(?:#.*)?$",
        text,
    )
    if len(matches) != 1:
        raise BoardError(f"Marker must contain exactly one {key}")
    return matches[0].strip().strip("`\"'")


def _optional_marker_value(text: str, key: str) -> str | None:
    matches = re.findall(
        rf"(?mi)^\s*{re.escape(key)}\s*:\s*([^#\r\n]+?)\s*(?:#.*)?$",
        text,
    )
    if len(matches) > 1:
        raise BoardError(f"Marker must contain at most one {key}")
    if not matches:
        return None
    return matches[0].strip().strip("`\"'")


def _task_ceiling(value: str | None) -> int:
    if value is None:
        return DEFAULT_ACTIVE_TASK_CEILING
    if not re.fullmatch(r"[1-9][0-9]{0,3}", value):
        raise BoardError("active_task_ceiling must be an integer from 1 to 9999")
    return int(value)


def _load_marker(project_root: Path, *, require_enabled: bool = True) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    marker_path = project_root / ".codex" / "coordination" / "project.yaml"
    coordination_path = marker_path.parent
    if _is_linklike(project_root / ".codex") or _is_linklike(coordination_path):
        raise BoardError("The coordination path must not be a symlink or junction")
    if _is_linklike(marker_path):
        raise BoardError("The project marker must not be a symlink or junction")
    try:
        raw = marker_path.read_bytes()
    except OSError as error:
        raise BoardError(f"Cannot read project marker: {error}") from error
    if len(raw) > 16_384:
        raise BoardError("Project marker exceeds 16384 bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise BoardError("Project marker is not valid UTF-8") from error

    schema = _marker_value(text, "schema_version")
    enabled = _marker_value(text, "coordination_enabled").lower()
    project_id = _marker_value(text, "project_id")
    task_ceiling = _task_ceiling(_optional_marker_value(text, "active_task_ceiling"))
    if schema != str(MARKER_SCHEMA_VERSION):
        raise BoardError(
            f"Unsupported marker schema {schema!r}; expected {MARKER_SCHEMA_VERSION}. "
            "Keep Coordinator disabled and run the documented migration."
        )
    if enabled not in {"true", "false"}:
        raise BoardError("coordination_enabled must be true or false")
    if require_enabled and enabled != "true":
        raise BoardError("The task-boundary board is disabled for this project")
    if not PROJECT_ID.fullmatch(project_id):
        raise BoardError("project_id is invalid")
    if _marker_value(text, "cross_project_task_access") != "false":
        raise BoardError("cross_project_task_access must be false")
    if _marker_value(text, "cross_project_state_changes") != "false":
        raise BoardError("cross_project_state_changes must be false")
    if _marker_value(text, "active") != ".codex/coordination/active":
        raise BoardError("Marker active path is incompatible")
    if _marker_value(text, "archive") != ".codex/coordination/archive":
        raise BoardError("Marker archive path is incompatible")

    coordination_root = marker_path.parent.resolve(strict=False)
    active_root = (project_root / ".codex" / "coordination" / "active").resolve(
        strict=False
    )
    archive_root = (project_root / ".codex" / "coordination" / "archive").resolve(
        strict=False
    )
    for label, path in (("active", active_root), ("archive", archive_root)):
        try:
            path.relative_to(coordination_root)
        except ValueError as error:
            raise BoardError(f"Marker {label} path escapes the coordination root") from error
    for label, lexical in (
        ("active", coordination_path / "active"),
        ("archive", coordination_path / "archive"),
    ):
        if _is_linklike(lexical):
            raise BoardError(f"The {label} board path must not be a symlink or junction")

    return {
        "projectRoot": project_root,
        "coordinationRoot": coordination_root,
        "activeRoot": active_root,
        "archiveRoot": archive_root,
        "projectId": project_id,
        "taskCeiling": task_ceiling,
        "enabled": enabled == "true",
    }


def _valid_text(value: Any, *, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise BoardError(f"{label} must be text")
    value = value.strip()
    if not 1 <= len(value) <= maximum:
        raise BoardError(f"{label} must contain 1 to {maximum} characters")
    if any(
        character in {"\r", "\n", "\u2028", "\u2029"}
        or unicodedata.category(character) in {"Cc", "Cs"}
        for character in value
    ):
        raise BoardError(f"{label} contains unsupported control text")
    return value


def _timestamp(value: Any, *, label: str) -> str:
    value = _valid_text(value, label=label, maximum=40)
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise BoardError(f"{label} is not ISO-8601") from error
    if parsed.utcoffset() is None or "T" not in value:
        raise BoardError(f"{label} must include a timezone")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_path(value: str) -> str:
    value = _valid_text(value, label="claim path", maximum=240).replace("\\", "/")
    if value == ".":
        return value
    if any(character in value for character in "*?[]") or ":" in value:
        raise BoardError(f"Claim path must be a concrete repository-relative path: {value}")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise BoardError(f"Claim path escapes or ambiguously names the repository: {value}")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise BoardError(f"Claim path escapes or ambiguously names the repository: {value}")
    return path.as_posix()


def _deduplicate(values: list[str], *, label: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            raise BoardError(f"Duplicate {label}: {value}")
        seen.add(key)
        result.append(value)
    return result


def _string_items(value: Any, *, label: str, maximum: int) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise BoardError(f"Claim has too many {label}s")
    if any(not isinstance(item, str) for item in value):
        raise BoardError(f"Every claim {label} must be text")
    return value


def _validate_claim(value: dict[str, Any], *, project_id: str, filename: str) -> dict[str, Any]:
    unknown = set(value) - CLAIM_KEYS
    missing = CLAIM_KEYS - set(value)
    if unknown:
        raise BoardError(
            f"Claim {filename} contains unsupported fields: {', '.join(sorted(unknown))}"
        )
    if missing:
        raise BoardError(f"Claim {filename} is missing fields: {', '.join(sorted(missing))}")
    if value["schemaVersion"] != CLAIM_SCHEMA_VERSION:
        raise BoardError(f"Claim {filename} has an unsupported schema")
    if value["projectId"] != project_id:
        raise BoardError(f"Claim {filename} belongs to another project")
    thread_id = value["threadId"]
    if not isinstance(thread_id, str) or not THREAD_ID.fullmatch(thread_id):
        raise BoardError(f"Claim {filename} has an invalid threadId")
    if filename != f"{thread_id}.json":
        raise BoardError(f"Claim filename does not match its threadId: {filename}")
    title = _valid_text(value["title"], label="title", maximum=120)
    goal = _valid_text(value["goal"], label="goal", maximum=320)
    status = value["status"]
    if status not in {"active", "blocked"}:
        raise BoardError(f"Claim {filename} has an invalid status")
    revision = value["revision"]
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise BoardError(f"Claim {filename} has an invalid revision")
    created_at = _timestamp(value["createdAt"], label="createdAt")
    updated_at = _timestamp(value["updatedAt"], label="updatedAt")

    paths = _string_items(value["paths"], label="path", maximum=MAX_PATHS)
    actions = _string_items(value["actions"], label="action", maximum=MAX_ACTIONS)
    blocked_by = _string_items(
        value["blockedBy"], label="dependency", maximum=MAX_DEPENDENCIES
    )
    paths = _deduplicate([_normalize_path(item) for item in paths], label="path")
    actions = _deduplicate(actions, label="action")
    for action in actions:
        if not ACTION.fullmatch(action):
            raise BoardError(f"Claim {filename} has an invalid action: {action}")
    dependencies = _deduplicate(blocked_by, label="dependency")
    for dependency in dependencies:
        if not THREAD_ID.fullmatch(dependency) or dependency == thread_id:
            raise BoardError(f"Claim {filename} has an invalid dependency")
    if not paths and not actions:
        raise BoardError(f"Claim {filename} must own at least one path or action")
    if not isinstance(value["limitOverride"], bool):
        raise BoardError(f"Claim {filename} has an invalid limitOverride")
    return {
        **value,
        "title": title,
        "goal": goal,
        "createdAt": created_at,
        "updatedAt": updated_at,
        "paths": paths,
        "actions": actions,
        "blockedBy": dependencies,
    }


def _active_records(marker: dict[str, Any]) -> list[dict[str, Any]]:
    active_root: Path = marker["activeRoot"]
    if not active_root.exists():
        return []
    if not active_root.is_dir() or active_root.is_symlink():
        raise BoardError("The active board path is not a normal directory")
    paths = sorted(active_root.glob("*.json"), key=lambda item: item.name.casefold())
    records: list[dict[str, Any]] = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise BoardError(f"Active claim is not a normal file: {path.name}")
        records.append(
            _validate_claim(
                _read_json(path), project_id=marker["projectId"], filename=path.name
            )
        )
    return records


def _path_overlap(left: str, right: str) -> bool:
    if left == "." or right == ".":
        return True
    left_parts = tuple(part.casefold() for part in PurePosixPath(left).parts)
    right_parts = tuple(part.casefold() for part in PurePosixPath(right).parts)
    common = min(len(left_parts), len(right_parts))
    return left_parts[:common] == right_parts[:common]


def _overlaps(
    candidate: dict[str, Any], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    overlaps: list[dict[str, Any]] = []
    for record in records:
        if record["threadId"] == candidate["threadId"]:
            continue
        path_pairs = sorted(
            {
                (left, right)
                for left in candidate["paths"]
                for right in record["paths"]
                if _path_overlap(left, right)
            }
        )
        action_overlap = sorted(
            set(candidate["actions"]).intersection(record["actions"])
        )
        if path_pairs or action_overlap:
            overlaps.append(
                {
                    "threadId": record["threadId"],
                    "title": record["title"],
                    "goal": record["goal"],
                    "pathOverlaps": [
                        {"requested": left, "owned": right}
                        for left, right in path_pairs
                    ],
                    "actionOverlaps": action_overlap,
                }
            )
    return overlaps


def _warnings(
    candidate: dict[str, Any], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Report possible shared-file work without turning task scope into a lock."""

    warnings: list[dict[str, Any]] = []
    for overlap in _overlaps(candidate, records):
        advisory_actions = [
            action
            for action in overlap["actionOverlaps"]
            if action in LEGACY_ADVISORY_ACTIONS
        ]
        if overlap["pathOverlaps"] or advisory_actions:
            warnings.append(
                {
                    **overlap,
                    "actionOverlaps": advisory_actions,
                }
            )
    return warnings


def _conflicts(candidate: dict[str, Any], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only conflicts that must have one active owner."""

    conflicts: list[dict[str, Any]] = []
    for overlap in _overlaps(candidate, records):
        blocking_actions = [
            action
            for action in overlap["actionOverlaps"]
            if action not in LEGACY_ADVISORY_ACTIONS
        ]
        if blocking_actions:
            conflicts.append(
                {
                    **overlap,
                    "pathOverlaps": [],
                    "actionOverlaps": blocking_actions,
                }
            )
    return conflicts


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_linklike(path.parent):
        raise BoardError(
            f"Refusing to write through a linked board directory: {path.parent}"
        )
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            temporary_name = stream.name
        os.replace(temporary_name, path)
    except OSError as error:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise BoardError(f"Cannot write board record {path.name}: {error}") from error


@contextmanager
def _board_write_lock(marker: dict[str, Any]):
    """Serialize claim mutations without creating another state authority."""

    active_root: Path = marker["activeRoot"]
    active_root.mkdir(parents=True, exist_ok=True)
    if _is_linklike(active_root) or not active_root.is_dir():
        raise BoardError("The active board path is not a normal directory")
    lock_path = active_root / ".write.lock"
    if _is_linklike(lock_path):
        raise BoardError("The board lock must not be a symlink or junction")
    try:
        with lock_path.open("a+b") as stream:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    if os.fstat(stream.fileno()).st_size == 0:
                        stream.seek(0)
                        stream.write(b"\0")
                        stream.flush()
                        os.fsync(stream.fileno())
                    yield
                finally:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    except OSError as error:
        raise BoardError(f"Cannot lock the active board: {error}") from error


def _encode(value: dict[str, Any]) -> bytes:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_RECORD_BYTES:
        raise BoardError(f"Board record exceeds {MAX_RECORD_BYTES} bytes")
    return payload


def _markdown_cell(value: str) -> str:
    """Keep validated claim text inert inside the generated Markdown table."""

    return (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _render_current_view(marker: dict[str, Any], records: list[dict[str, Any]]) -> bytes:
    """Render the small human view from canonical active claims only."""

    coordinators = [
        record for record in records if "goal-coordination" in record["actions"]
    ]
    lines = [
        "# Current coordinated work",
        "",
        "> Generated active-only view. Schema-2 JSON claims in `active/` are canonical.",
        "",
        f"Project: `{marker['projectId']}`",
        f"Active lanes: {len(records)}",
        f"Active task ceiling: {marker['taskCeiling']}",
    ]
    if len(coordinators) == 1:
        coordinator = coordinators[0]
        lines.extend(
            (
                "Coordinator: "
                f"`{coordinator['threadId']}` — {_markdown_cell(coordinator['title'])}",
                f"Shared goal: {_markdown_cell(coordinator['goal'])}",
            )
        )
    lines.extend(
        (
            "",
            "| Task | Goal | Owns | Status | Depends on |",
            "| --- | --- | --- | --- | --- |",
        )
    )
    for record in records:
        task = f"{_markdown_cell(record['title'])} (`{record['threadId']}`)"
        ownership = [f"path: {path}" for path in record["paths"]]
        ownership.extend(f"action: {action}" for action in record["actions"])
        dependencies = record["blockedBy"] or ["—"]
        lines.append(
            "| "
            + " | ".join(
                (
                    task,
                    _markdown_cell(record["goal"]),
                    _markdown_cell(", ".join(ownership)),
                    record["status"],
                    _markdown_cell(", ".join(dependencies)),
                )
            )
            + " |"
        )
    if not records:
        lines.append("| — | — | — | — | — |")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _refresh_current_view(
    marker: dict[str, Any], records: list[dict[str, Any]]
) -> bool:
    """Best-effort refresh; a derived view can never veto canonical state."""

    try:
        _atomic_write(
            marker["coordinationRoot"] / CURRENT_VIEW_NAME,
            _render_current_view(marker, records),
        )
    except (BoardError, OSError, UnicodeError):
        return False
    return True


def list_board(project_root: Path) -> dict[str, Any]:
    marker = _load_marker(project_root)
    records = _active_records(marker)
    conflicts: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for record in records:
        conflicts.extend(
            {
                "requestedBy": record["threadId"],
                **conflict,
            }
            for conflict in _conflicts(record, records)
            if record["threadId"] < conflict["threadId"]
        )
        warnings.extend(
            {
                "requestedBy": record["threadId"],
                **warning,
            }
            for warning in _warnings(record, records)
            if record["threadId"] < warning["threadId"]
        )
    return {
        "status": "ok" if not conflicts else "conflict",
        "schemaVersion": MARKER_SCHEMA_VERSION,
        "projectId": marker["projectId"],
        "activeCount": len(records),
        "defaultLimit": marker["taskCeiling"],
        "hardLimit": None,
        "records": records,
        "conflicts": conflicts,
        "warnings": warnings,
    }


def assignment_identity(
    project_root: Path,
    *,
    coordinator_thread_id: str,
    lane_key: str,
) -> dict[str, Any]:
    """Create one stable, non-secret ID for a lane in the active goal instance."""

    marker = _load_marker(project_root)
    if not THREAD_ID.fullmatch(coordinator_thread_id):
        raise BoardError("coordinator-thread-id must be an exact native Codex thread UUID")
    if not LANE_KEY.fullmatch(lane_key):
        raise BoardError(
            "lane-key must be a lowercase slug with at most 64 characters"
        )
    coordinators = [
        record
        for record in _active_records(marker)
        if "goal-coordination" in record["actions"]
    ]
    if len(coordinators) != 1:
        raise BoardError("The active board must contain exactly one goal Coordinator")
    coordinator = coordinators[0]
    if coordinator["threadId"] != coordinator_thread_id:
        raise BoardError("coordinator-thread-id does not own goal-coordination")
    material = json.dumps(
        [
            marker["projectId"],
            coordinator_thread_id,
            coordinator["createdAt"],
            lane_key,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assignment_id = "ga-" + hashlib.sha256(material).hexdigest()[:32]
    return {
        "status": "ok",
        "projectId": marker["projectId"],
        "coordinatorThreadId": coordinator_thread_id,
        "laneKey": lane_key,
        "assignmentId": assignment_id,
    }


def reconcile_assignment_receipt(
    *,
    assignment_id: str,
    observed_assignment_ids: list[str],
    outcome: str,
) -> dict[str, Any]:
    """Classify one native create or send without ever guessing that it failed."""

    if not ASSIGNMENT_ID.fullmatch(assignment_id):
        raise BoardError("assignment-id is invalid")
    if outcome not in {"not-attempted", "ambiguous", "confirmed"}:
        raise BoardError("outcome must be not-attempted, ambiguous, or confirmed")
    if not isinstance(observed_assignment_ids, list) or len(observed_assignment_ids) > 100:
        raise BoardError("observed-assignment-id accepts at most 100 values")
    for observed in observed_assignment_ids:
        if not isinstance(observed, str) or not ASSIGNMENT_ID.fullmatch(observed):
            raise BoardError("observed-assignment-id is invalid")

    matches = sum(value == assignment_id for value in observed_assignment_ids)
    if matches > 1:
        decision = "stop-duplicate"
    elif matches == 1:
        decision = "use-existing"
    elif outcome == "not-attempted":
        decision = "safe-to-attempt"
    elif outcome == "ambiguous":
        decision = "stop-unknown"
    else:
        decision = "stop-missing-receipt"
    return {
        "status": "ok",
        "assignmentId": assignment_id,
        "outcome": outcome,
        "matches": matches,
        "decision": decision,
    }


def _pending_notice_identity(
    marker: dict[str, Any],
    *,
    assignment_id: str,
    kind: str,
    sender_thread_id: str,
    recipient_thread_id: str,
) -> tuple[str, Path]:
    if not isinstance(assignment_id, str) or not ASSIGNMENT_ID.fullmatch(
        assignment_id
    ):
        raise BoardError("assignment-id is invalid")
    if not isinstance(kind, str) or kind not in NOTICE_KINDS:
        raise BoardError("kind must be GOAL_ASSIGNMENT or RESULT_READY")
    for label, value in (
        ("sender-thread-id", sender_thread_id),
        ("recipient-thread-id", recipient_thread_id),
    ):
        if not isinstance(value, str) or not THREAD_ID.fullmatch(value):
            raise BoardError(f"{label} must be an exact native Codex thread UUID")
    if sender_thread_id == recipient_thread_id:
        raise BoardError("sender-thread-id and recipient-thread-id must differ")

    material = json.dumps(
        [
            marker["projectId"],
            assignment_id,
            kind,
            sender_thread_id,
            recipient_thread_id,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    notice_id = "pn-" + hashlib.sha256(material).hexdigest()[:32]
    pending_root = marker["coordinationRoot"] / PENDING_NOTICE_DIRECTORY
    resolved_root = pending_root.resolve(strict=False)
    try:
        resolved_root.relative_to(marker["coordinationRoot"])
    except ValueError as error:
        raise BoardError("The pending-delivery path escapes the coordination root") from error
    if _is_linklike(pending_root):
        raise BoardError("The pending-delivery path must not be a symlink or junction")

    recipient_root = pending_root / recipient_thread_id
    if _is_linklike(recipient_root):
        raise BoardError(
            "The pending-delivery recipient path must not be a symlink or junction"
        )
    return notice_id, recipient_root / f"{notice_id}.json"


def _validate_pending_notice(
    value: dict[str, Any],
    *,
    marker: dict[str, Any],
    filename: str,
) -> dict[str, Any]:
    if set(value) != PENDING_NOTICE_KEYS:
        missing = sorted(PENDING_NOTICE_KEYS - set(value))
        extra = sorted(set(value) - PENDING_NOTICE_KEYS)
        raise BoardError(
            f"Pending delivery record {filename} has unsupported fields; "
            f"missing={missing}, extra={extra}"
        )
    if value["schemaVersion"] != 1:
        raise BoardError(f"Pending delivery record {filename} has an unsupported schema")
    if value["projectId"] != marker["projectId"]:
        raise BoardError(f"Pending delivery record {filename} belongs to another project")
    notice_id, expected_path = _pending_notice_identity(
        marker,
        assignment_id=value["assignmentId"],
        kind=value["kind"],
        sender_thread_id=value["senderThreadId"],
        recipient_thread_id=value["recipientThreadId"],
    )
    if value["noticeId"] != notice_id or filename != expected_path.name:
        raise BoardError(f"Pending delivery record filename or identity is invalid: {filename}")
    if value["repository"] != str(marker["projectRoot"]):
        raise BoardError(f"Pending delivery record {filename} names another repository")
    if value["deliveryState"] != "pending":
        raise BoardError(f"Pending delivery record {filename} has an invalid delivery state")
    _timestamp(value["createdAt"], label="pending delivery record createdAt")
    return value


def _pending_notice_records(
    marker: dict[str, Any], *, recipient_thread_id: str
) -> list[dict[str, Any]]:
    if not isinstance(recipient_thread_id, str) or not THREAD_ID.fullmatch(
        recipient_thread_id
    ):
        raise BoardError(
            "recipient-thread-id must be an exact native Codex thread UUID"
        )
    pending_root = marker["coordinationRoot"] / PENDING_NOTICE_DIRECTORY
    if _is_linklike(pending_root):
        raise BoardError("The pending-delivery path must not be a symlink or junction")
    recipient_root = pending_root / recipient_thread_id
    if not recipient_root.exists():
        return []
    if _is_linklike(recipient_root) or not recipient_root.is_dir():
        raise BoardError(
            "The pending-delivery recipient path is not a normal directory"
        )
    paths = sorted(recipient_root.iterdir(), key=lambda item: item.name.casefold())
    if len(paths) > MAX_PENDING_NOTICES_PER_RECIPIENT:
        raise BoardError(
            "The recipient has too many pending delivery records; inspect this project manually"
        )
    records: list[dict[str, Any]] = []
    for path in paths:
        if (
            _is_linklike(path)
            or not path.is_file()
            or not path.name.endswith(".json")
            or not NOTICE_ID.fullmatch(path.stem)
        ):
            raise BoardError(
                f"Pending delivery record is not a normal recognized file: {path.name}"
            )
        records.append(
            _validate_pending_notice(
                _read_json(path),
                marker=marker,
                filename=path.name,
            )
        )
    return records


def create_pending_notice(
    project_root: Path,
    *,
    assignment_id: str,
    kind: str,
    sender_thread_id: str,
    recipient_thread_id: str,
) -> dict[str, Any]:
    """Persist one routing-only fact after a native send has no visible receipt."""

    marker = _load_marker(project_root)
    notice_id, target = _pending_notice_identity(
        marker,
        assignment_id=assignment_id,
        kind=kind,
        sender_thread_id=sender_thread_id,
        recipient_thread_id=recipient_thread_id,
    )
    with _board_write_lock(marker):
        coordinators = [
            record
            for record in _active_records(marker)
            if "goal-coordination" in record["actions"]
        ]
        if len(coordinators) != 1:
            raise BoardError(
                "The active board must contain exactly one goal Coordinator"
            )
        coordinator_thread_id = coordinators[0]["threadId"]
        expected_coordinator = (
            sender_thread_id if kind == "GOAL_ASSIGNMENT" else recipient_thread_id
        )
        if coordinator_thread_id != expected_coordinator:
            raise BoardError(
                "The pending delivery record does not route through the active goal Coordinator"
            )

        if target.exists():
            if _is_linklike(target) or not target.is_file():
                raise BoardError("The pending delivery record is not a normal file")
            record = _validate_pending_notice(
                _read_json(target),
                marker=marker,
                filename=target.name,
            )
            return {
                "status": "existing",
                "projectId": marker["projectId"],
                "record": record,
            }

        records = _pending_notice_records(
            marker, recipient_thread_id=recipient_thread_id
        )
        if len(records) >= MAX_PENDING_NOTICES_PER_RECIPIENT:
            raise BoardError(
                "The recipient already has the maximum number of pending delivery records"
            )
        record = {
            "schemaVersion": 1,
            "noticeId": notice_id,
            "projectId": marker["projectId"],
            "assignmentId": assignment_id,
            "kind": kind,
            "senderThreadId": sender_thread_id,
            "recipientThreadId": recipient_thread_id,
            "repository": str(marker["projectRoot"]),
            "deliveryState": "pending",
            "createdAt": _now(),
        }
        _validate_pending_notice(record, marker=marker, filename=target.name)
        if _is_linklike(target):
            raise BoardError("The pending delivery record must not be a symlink or junction")
        _atomic_write(target, _encode(record))
        return {
            "status": "created",
            "projectId": marker["projectId"],
            "record": record,
        }


def list_pending_notices(
    project_root: Path, *, recipient_thread_id: str
) -> dict[str, Any]:
    """Read only the pending delivery records routed to one exact native task."""

    marker = _load_marker(project_root)
    records = _pending_notice_records(
        marker, recipient_thread_id=recipient_thread_id
    )
    return {
        "status": "ok",
        "projectId": marker["projectId"],
        "recipientThreadId": recipient_thread_id,
        "pendingCount": len(records),
        "records": records,
    }


def resolve_pending_notice(
    project_root: Path,
    *,
    assignment_id: str,
    kind: str,
    sender_thread_id: str,
    recipient_thread_id: str,
    actor_thread_id: str,
    evidence: str,
) -> dict[str, Any]:
    """Delete one fallback fact after native receipt or recipient action is verified."""

    marker = _load_marker(project_root)
    notice_id, target = _pending_notice_identity(
        marker,
        assignment_id=assignment_id,
        kind=kind,
        sender_thread_id=sender_thread_id,
        recipient_thread_id=recipient_thread_id,
    )
    if not isinstance(actor_thread_id, str) or not THREAD_ID.fullmatch(
        actor_thread_id
    ):
        raise BoardError("actor-thread-id must be an exact native Codex thread UUID")
    if actor_thread_id not in {sender_thread_id, recipient_thread_id}:
        raise BoardError("Only the sender or recipient may resolve a pending delivery record")
    expected_evidence = (
        "native-receipt"
        if actor_thread_id == sender_thread_id
        else "recipient-action"
    )
    if evidence != expected_evidence:
        raise BoardError(
            f"This actor must use evidence={expected_evidence}"
        )

    with _board_write_lock(marker):
        if not target.is_file() or _is_linklike(target):
            raise BoardError("No matching pending delivery record exists")
        _validate_pending_notice(
            _read_json(target),
            marker=marker,
            filename=target.name,
        )
        try:
            target.unlink()
        except OSError as error:
            raise BoardError(
                f"Cannot resolve pending delivery record {target.name}: {error}"
            ) from error
    return {
        "status": "resolved",
        "projectId": marker["projectId"],
        "noticeId": notice_id,
        "evidence": evidence,
    }


def claim_boundary(
    project_root: Path,
    *,
    thread_id: str,
    title: str,
    goal: str,
    paths: list[str],
    actions: list[str],
    blocked_by: list[str],
    status: str,
    expected_revision: int,
    user_approved_over_limit: bool,
) -> dict[str, Any]:
    marker = _load_marker(project_root)
    if not THREAD_ID.fullmatch(thread_id):
        raise BoardError("thread-id must be an exact native Codex thread UUID")
    if (
        not isinstance(expected_revision, int)
        or isinstance(expected_revision, bool)
        or expected_revision < 0
    ):
        raise BoardError("expected-revision must be a non-negative integer")
    if not isinstance(user_approved_over_limit, bool):
        raise BoardError("user-approved-over-limit must be a boolean")
    with _board_write_lock(marker):
        return _claim_boundary_locked(
            marker,
            thread_id=thread_id,
            title=title,
            goal=goal,
            paths=paths,
            actions=actions,
            blocked_by=blocked_by,
            status=status,
            expected_revision=expected_revision,
            user_approved_over_limit=user_approved_over_limit,
        )


def _claim_boundary_locked(
    marker: dict[str, Any],
    *,
    thread_id: str,
    title: str,
    goal: str,
    paths: list[str],
    actions: list[str],
    blocked_by: list[str],
    status: str,
    expected_revision: int,
    user_approved_over_limit: bool,
) -> dict[str, Any]:
    records = _active_records(marker)
    existing = next((item for item in records if item["threadId"] == thread_id), None)
    current_revision = existing["revision"] if existing else 0
    if expected_revision != current_revision:
        raise BoardError(
            f"Claim revision changed: expected {expected_revision}, found {current_revision}"
        )
    if (
        existing is None
        and len(records) >= marker["taskCeiling"]
        and not user_approved_over_limit
    ):
        raise BoardError(
            f"Active task ceiling of {marker['taskCeiling']} reached. "
            "Ask the user to approve an exact temporary ceiling or update the project ceiling."
        )
    normalized_paths = _deduplicate(
        [
            _normalize_path(value)
            for value in _string_items(paths, label="path", maximum=MAX_PATHS)
        ],
        label="path",
    )
    normalized_actions = _deduplicate(
        _string_items(actions, label="action", maximum=MAX_ACTIONS), label="action"
    )
    for action in normalized_actions:
        if not ACTION.fullmatch(action):
            raise BoardError(f"Invalid action claim: {action}")
    dependencies = _deduplicate(
        _string_items(
            blocked_by, label="dependency", maximum=MAX_DEPENDENCIES
        ),
        label="dependency",
    )
    for dependency in dependencies:
        if not THREAD_ID.fullmatch(dependency) or dependency == thread_id:
            raise BoardError(f"Invalid dependency thread ID: {dependency}")
    if not normalized_paths and not normalized_actions:
        raise BoardError("A claim must include at least one path or exclusive action")
    if status not in {"active", "blocked"}:
        raise BoardError("status must be active or blocked")

    now = _now()
    candidate = {
        "schemaVersion": CLAIM_SCHEMA_VERSION,
        "projectId": marker["projectId"],
        "threadId": thread_id,
        "title": _valid_text(title, label="title", maximum=120),
        "goal": _valid_text(goal, label="goal", maximum=320),
        "status": status,
        "revision": current_revision + 1,
        "createdAt": existing["createdAt"] if existing else now,
        "updatedAt": now,
        "paths": normalized_paths,
        "actions": normalized_actions,
        "blockedBy": dependencies,
        "limitOverride": bool(
            (existing and existing["limitOverride"]) or user_approved_over_limit
        ),
    }
    candidate = _validate_claim(
        candidate, project_id=marker["projectId"], filename=f"{thread_id}.json"
    )
    conflicts = _conflicts(candidate, records)
    if conflicts:
        raise ClaimConflict(conflicts)

    target = marker["activeRoot"] / f"{thread_id}.json"
    if _is_linklike(target):
        raise BoardError("The task claim must not be a symlink or junction")
    previous = target.read_bytes() if target.is_file() else None
    _atomic_write(target, _encode(candidate))
    try:
        post_records = _active_records(marker)
        post_conflicts = _conflicts(candidate, post_records)
        if post_conflicts:
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                _atomic_write(target, previous)
            raise ClaimConflict(post_conflicts)
    except (BoardError, OSError):
        if previous is None and target.exists():
            try:
                target.unlink()
            except OSError:
                pass
        elif previous is not None:
            try:
                _atomic_write(target, previous)
            except BoardError:
                pass
        raise

    _refresh_current_view(marker, post_records)

    return {
        "status": "claimed" if existing is None else "updated",
        "projectId": marker["projectId"],
        "record": candidate,
        "activeCount": len(post_records),
        "taskCeiling": marker["taskCeiling"],
        "warnings": _warnings(candidate, post_records),
    }


def release_boundary(
    project_root: Path,
    *,
    thread_id: str,
    expected_revision: int,
    final_status: str,
) -> dict[str, Any]:
    marker = _load_marker(project_root)
    if not THREAD_ID.fullmatch(thread_id):
        raise BoardError("thread-id must be an exact native Codex thread UUID")
    if (
        not isinstance(expected_revision, int)
        or isinstance(expected_revision, bool)
        or expected_revision < 1
    ):
        raise BoardError("expected-revision must be a positive integer")
    with _board_write_lock(marker):
        return _release_boundary_locked(
            marker,
            thread_id=thread_id,
            expected_revision=expected_revision,
            final_status=final_status,
        )


def _release_boundary_locked(
    marker: dict[str, Any],
    *,
    thread_id: str,
    expected_revision: int,
    final_status: str,
) -> dict[str, Any]:
    records = _active_records(marker)
    record = next((item for item in records if item["threadId"] == thread_id), None)
    if record is None:
        raise BoardError("No active claim exists for this thread")
    if record["revision"] != expected_revision:
        raise BoardError(
            f"Claim revision changed: expected {expected_revision}, found {record['revision']}"
        )
    if final_status not in {
        "completed",
        "stopped",
        "superseded",
        "stale-owner-confirmed",
    }:
        raise BoardError("Invalid final status")

    closed_at = _now()
    receipt = {
        "schemaVersion": CLAIM_SCHEMA_VERSION,
        "projectId": marker["projectId"],
        "threadId": thread_id,
        "title": record["title"],
        "goal": record["goal"],
        "finalStatus": final_status,
        "lastRevision": record["revision"],
        "closedAt": closed_at,
    }
    archive_root: Path = marker["archiveRoot"]
    archive_root.mkdir(parents=True, exist_ok=True)
    if _is_linklike(archive_root):
        raise BoardError("The archive path must not be a symlink or junction")
    stamp = closed_at.replace(":", "").replace("-", "")
    payload = _encode(receipt)
    archive_path: Path | None = None
    try:
        for ordinal in range(10_000):
            suffix = "" if ordinal == 0 else f"-{ordinal}"
            candidate = archive_root / f"{thread_id}-{stamp}{suffix}.json"
            try:
                with candidate.open("xb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                archive_path = candidate
                break
            except FileExistsError:
                continue
        if archive_path is None:
            raise OSError("Cannot allocate a unique compact receipt name")
        (marker["activeRoot"] / f"{thread_id}.json").unlink()
    except OSError as error:
        try:
            if archive_path is not None:
                archive_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise BoardError(f"Cannot release claim safely: {error}") from error
    _refresh_current_view(
        marker,
        [item for item in records if item["threadId"] != thread_id],
    )
    return {
        "status": "released",
        "projectId": marker["projectId"],
        "receipt": receipt,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    listing = commands.add_parser("list", help="read the bounded active board")
    listing.add_argument("--project-root", required=True, type=Path)

    assignment = commands.add_parser(
        "assignment-id", help="derive an idempotent ID for one goal lane"
    )
    assignment.add_argument("--project-root", required=True, type=Path)
    assignment.add_argument("--coordinator-thread-id", required=True)
    assignment.add_argument("--lane-key", required=True)

    receipt = commands.add_parser(
        "mutation-receipt", help="classify one native create or send readback"
    )
    receipt.add_argument("--assignment-id", required=True)
    receipt.add_argument(
        "--outcome",
        required=True,
        choices=("not-attempted", "ambiguous", "confirmed"),
    )
    receipt.add_argument("--observed-assignment-id", action="append", default=[])

    pending_create = commands.add_parser(
        "pending-create",
        help="record one native assignment or terminal return with no visible receipt",
    )
    pending_create.add_argument("--project-root", required=True, type=Path)
    pending_create.add_argument("--assignment-id", required=True)
    pending_create.add_argument(
        "--kind", required=True, choices=tuple(sorted(NOTICE_KINDS))
    )
    pending_create.add_argument("--sender-thread-id", required=True)
    pending_create.add_argument("--recipient-thread-id", required=True)

    pending_list = commands.add_parser(
        "pending-list", help="read pending delivery records for one exact recipient task"
    )
    pending_list.add_argument("--project-root", required=True, type=Path)
    pending_list.add_argument("--recipient-thread-id", required=True)

    pending_resolve = commands.add_parser(
        "pending-resolve",
        help="remove one delivery record after verified native receipt or recipient action",
    )
    pending_resolve.add_argument("--project-root", required=True, type=Path)
    pending_resolve.add_argument("--assignment-id", required=True)
    pending_resolve.add_argument(
        "--kind", required=True, choices=tuple(sorted(NOTICE_KINDS))
    )
    pending_resolve.add_argument("--sender-thread-id", required=True)
    pending_resolve.add_argument("--recipient-thread-id", required=True)
    pending_resolve.add_argument("--actor-thread-id", required=True)
    pending_resolve.add_argument(
        "--evidence",
        required=True,
        choices=("native-receipt", "recipient-action"),
    )

    claim = commands.add_parser("claim", help="create or update this task's claim")
    claim.add_argument("--project-root", required=True, type=Path)
    claim.add_argument("--thread-id", required=True)
    claim.add_argument("--title", required=True)
    claim.add_argument("--goal", required=True)
    claim.add_argument("--path", action="append", default=[])
    claim.add_argument("--action", action="append", default=[])
    claim.add_argument("--blocked-by", action="append", default=[])
    claim.add_argument("--status", choices=("active", "blocked"), default="active")
    claim.add_argument("--expected-revision", required=True, type=int)
    claim.add_argument(
        "--user-approved-over-limit",
        action="store_true",
        help="user approved this claim within an exact temporary ceiling above the project default",
    )

    release = commands.add_parser("release", help="move this task's claim to a cold receipt")
    release.add_argument("--project-root", required=True, type=Path)
    release.add_argument("--thread-id", required=True)
    release.add_argument("--expected-revision", required=True, type=int)
    release.add_argument(
        "--status",
        dest="final_status",
        required=True,
        choices=("completed", "stopped", "superseded", "stale-owner-confirmed"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "list":
            report = list_board(args.project_root)
        elif args.command == "assignment-id":
            report = assignment_identity(
                args.project_root,
                coordinator_thread_id=args.coordinator_thread_id,
                lane_key=args.lane_key,
            )
        elif args.command == "mutation-receipt":
            report = reconcile_assignment_receipt(
                assignment_id=args.assignment_id,
                observed_assignment_ids=args.observed_assignment_id,
                outcome=args.outcome,
            )
        elif args.command == "pending-create":
            report = create_pending_notice(
                args.project_root,
                assignment_id=args.assignment_id,
                kind=args.kind,
                sender_thread_id=args.sender_thread_id,
                recipient_thread_id=args.recipient_thread_id,
            )
        elif args.command == "pending-list":
            report = list_pending_notices(
                args.project_root,
                recipient_thread_id=args.recipient_thread_id,
            )
        elif args.command == "pending-resolve":
            report = resolve_pending_notice(
                args.project_root,
                assignment_id=args.assignment_id,
                kind=args.kind,
                sender_thread_id=args.sender_thread_id,
                recipient_thread_id=args.recipient_thread_id,
                actor_thread_id=args.actor_thread_id,
                evidence=args.evidence,
            )
        elif args.command == "claim":
            report = claim_boundary(
                args.project_root,
                thread_id=args.thread_id,
                title=args.title,
                goal=args.goal,
                paths=args.path,
                actions=args.action,
                blocked_by=args.blocked_by,
                status=args.status,
                expected_revision=args.expected_revision,
                user_approved_over_limit=args.user_approved_over_limit,
            )
        else:
            report = release_boundary(
                args.project_root,
                thread_id=args.thread_id,
                expected_revision=args.expected_revision,
                final_status=args.final_status,
            )
    except ClaimConflict as error:
        print(
            json.dumps(
                {"status": "conflict", "error": str(error), "conflicts": error.conflicts},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2
    except (BoardError, OSError, UnicodeError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, indent=2))
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
