#!/usr/bin/env python3
"""Load Coordinator context and start the optional local Mission Control observer."""

from __future__ import annotations

import codecs
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MARKER_LIMIT = 16_384
CURRENT_LIMIT = 32_768
GIT_TIMEOUT_SECONDS = 2.5

TOKEN = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,63}")
PROJECT = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
THREAD = re.compile(
    r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|NONE|UNAVAILABLE)"
)
BOOL = re.compile(r"(?:true|false)")
EPOCH = re.compile(r"\d{1,9}")


def _valid_name(value: str) -> bool:
    return (
        1 <= len(value) <= 120
        and "|" not in value
        and not any(
            character in {"\r", "\n", "\u2028", "\u2029"}
            or unicodedata.category(character) in {"Cc", "Cs"}
            for character in value
        )
    )


def _valid_shared_goal(value: str) -> bool:
    return (
        1 <= len(value) <= 512
        and not any(
            character in {"\r", "\n", "\u2028", "\u2029"}
            or unicodedata.category(character) in {"Cc", "Cs"}
            for character in value
        )
    )


def _valid_table_text(value: str, *, maximum: int = 512) -> bool:
    return (
        1 <= len(value) <= maximum
        and "|" not in value
        and not any(
            character in {"\r", "\n", "\u2028", "\u2029"}
            or unicodedata.category(character) in {"Cc", "Cs"}
            for character in value
        )
    )


def _valid_reconciliation(value: str) -> bool:
    if not 1 <= len(value) <= 64:
        return False
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return "T" in value and parsed.utcoffset() is not None


NAME: Callable[[str], bool] = _valid_name
SHARED_GOAL: Callable[[str], bool] = _valid_shared_goal
RECONCILIATION: Callable[[str], bool] = _valid_reconciliation

TASKLESS_ALIASES = {"", "-", "none", "n/a", "not applicable"}
NO_ACTIVE_GOAL_ALIASES = TASKLESS_ALIASES | {
    "no active coordinated goal",
    "no active coordinated goal.",
}

TERMINAL_PREFIXES = (
    "ACKED",
    "CANCELLED",
    "CLOSED",
    "COMPLETE",
    "COMPLETED",
    "DONE",
    "REJECTED",
    "STOPPED",
    "SUPERSEDED",
    "TERMINAL",
    "UNREGISTERED",
)


@dataclass(frozen=True)
class BoundedText:
    text: str
    truncated: bool
    invalid_utf8: bool


@dataclass(frozen=True)
class ParsedTable:
    rows: list[dict[str, str]]
    valid: bool
    warnings: list[str]


@dataclass(frozen=True)
class Session:
    thread_id: str
    thread_name: str
    scope_kind: str
    role: str
    task_id: str
    status: str
    accepts: str

    def owns_address(self, value: str) -> bool:
        candidate_thread = _safe(value, THREAD)
        if candidate_thread not in {"UNKNOWN", "NONE", "UNAVAILABLE"}:
            return candidate_thread == self.thread_id
        candidate_name = _safe(value, NAME)
        return candidate_name != "UNKNOWN" and candidate_name == self.thread_name


TABLE_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "registered_sessions": {
        "thread_id": ("Thread ID",),
        "thread_name": ("Thread name",),
        "scope_kind": ("Scope kind",),
        "role": ("Role",),
        "task_id": ("Task ID",),
        "status": ("Status",),
        "accepts": ("Accepts project messages",),
    },
    "active_tasks": {
        "task_id": ("Task ID",),
        "owner": ("Owner",),
        "role": ("Role",),
        "status": ("Status",),
    },
    "pending_commands": {
        "task_id": ("Task ID",),
        "message_id": ("Message ID",),
        "recipient": ("Recipient thread ID",),
        "message_type": ("Message type",),
        "status": ("Status",),
    },
    "paused_work": {
        "task_id": ("Task ID",),
        "owner": ("Owner",),
        "reason": ("Reason",),
        "resume_condition": ("Resume condition",),
        "status": ("Status",),
    },
    "resume_queue": {
        "task_id": ("Task ID",),
        "message_id": ("Message ID",),
        "resume_condition": ("Resume condition",),
        "status": ("Status",),
    },
    "blocked_decisions": {
        "decision_id": ("Decision ID",),
        "task_id": ("Task ID",),
        "decision_needed": ("Decision needed",),
        "status": ("Status",),
    },
    "excluded_tasks": {
        "thread_id": ("Thread ID",),
        "thread_name": ("Thread name",),
        "excluded_by": ("Excluded by",),
        "reason": ("Reason",),
        "status": ("Status",),
    },
}


def _safe(
    value: str,
    pattern: re.Pattern[str] | Callable[[str], bool],
    default: str = "UNKNOWN",
) -> str:
    cleaned = value.strip().strip("`")
    valid = pattern(cleaned) if callable(pattern) else bool(pattern.fullmatch(cleaned))
    return cleaned if valid else default


def _normalize_taskless(value: str) -> str:
    cleaned = value.strip().strip("`")
    return "NONE" if cleaned.lower() in TASKLESS_ALIASES else cleaned


def _normalize_shared_goal(value: str) -> str:
    cleaned = value.strip().strip("`")
    return "none" if cleaned.lower() in NO_ACTIVE_GOAL_ALIASES else cleaned


def _valid_address(value: str) -> bool:
    cleaned = value.strip().strip("`")
    if THREAD.fullmatch(cleaned):
        return cleaned not in {"NONE", "UNAVAILABLE"}
    return _valid_name(cleaned)


def _valid_table_row(slug: str, row: dict[str, str]) -> bool:
    def token(value: str) -> bool:
        return bool(TOKEN.fullmatch(value.strip().strip("`")))

    checks: dict[str, dict[str, Callable[[str], bool]]] = {
        "registered_sessions": {
            "thread_id": lambda value: bool(THREAD.fullmatch(value.strip().strip("`"))),
            "thread_name": _valid_name,
            "scope_kind": token,
            "role": token,
            "task_id": lambda value: token(_normalize_taskless(value)),
            "status": token,
            "accepts": lambda value: bool(BOOL.fullmatch(value.strip().strip("`"))),
        },
        "active_tasks": {
            "task_id": token,
            "owner": _valid_address,
            "role": token,
            "status": token,
        },
        "pending_commands": {
            "task_id": token,
            "message_id": token,
            "recipient": _valid_address,
            "message_type": token,
            "status": token,
        },
        "paused_work": {
            "task_id": token,
            "owner": _valid_address,
            "reason": _valid_table_text,
            "resume_condition": _valid_table_text,
            "status": token,
        },
        "resume_queue": {
            "task_id": token,
            "message_id": token,
            "resume_condition": _valid_table_text,
            "status": token,
        },
        "blocked_decisions": {
            "decision_id": token,
            "task_id": token,
            "decision_needed": _valid_table_text,
            "status": token,
        },
        "excluded_tasks": {
            "thread_id": lambda value: bool(THREAD.fullmatch(value.strip().strip("`")))
            and value.strip().strip("`") not in {"NONE", "UNAVAILABLE"},
            "thread_name": _valid_name,
            "excluded_by": lambda value: value.strip().strip("`") == "DIRECT_USER",
            "reason": _valid_table_text,
            "status": lambda value: value.strip().strip("`") in {"ACTIVE", "REMOVED"},
        },
    }
    return all(check(row[field]) for field, check in checks[slug].items())


def _unique_row_identity(slug: str, row: dict[str, str]) -> tuple[str, str] | None:
    if slug == "registered_sessions":
        thread_id = row["thread_id"].strip().strip("`")
        identity = thread_id if thread_id not in {"NONE", "UNAVAILABLE"} else row[
            "thread_name"
        ].strip().strip("`")
        return "thread_id", identity
    fields = {
        "active_tasks": ("task_id", "task_id"),
        "pending_commands": ("message_id", "message_id"),
        "paused_work": ("task_id", "task_id"),
        "resume_queue": ("message_id", "message_id"),
        "blocked_decisions": ("decision_id", "decision_id"),
        "excluded_tasks": ("thread_id", "thread_id"),
    }
    field = fields.get(slug)
    if field is None:
        return None
    return field[0], row[field[1]].strip().strip("`")


def _required_field(
    text: str,
    label: str,
    pattern: re.Pattern[str] | Callable[[str], bool],
    default: str,
) -> str:
    occurrences = re.findall(
        rf"(?m)^\s*\*\*{re.escape(label)}:\*\*",
        text,
    )
    if len(occurrences) != 1:
        return default
    match = re.search(
        rf"(?m)^\s*\*\*{re.escape(label)}:\*\*\s+(?:`([^`\r\n]+)`|([^\r\n]+?))\s*$",
        text,
    )
    if not match:
        return default
    return _safe(match.group(1) or match.group(2), pattern, default)


def _read_bounded(path: Path, limit: int) -> BoundedText:
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    truncated = len(raw) > limit
    bounded = raw[:limit]
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    try:
        text = decoder.decode(bounded, final=not truncated)
        invalid_utf8 = False
    except UnicodeDecodeError:
        text = bounded.decode("utf-8", errors="replace")
        invalid_utf8 = True
    return BoundedText(text=text, truncated=truncated, invalid_utf8=invalid_utf8)


def _decode_git_output(value: bytes) -> str:
    """Decode Git paths with the same rules Python uses for filesystem paths."""
    try:
        return os.fsdecode(value)
    except UnicodeDecodeError:
        return value.decode("utf-8", errors="surrogateescape")


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    command = ["git", "-C", str(cwd), *args]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return subprocess.CompletedProcess(
        command,
        result.returncode,
        _decode_git_output(result.stdout),
        _decode_git_output(result.stderr),
    )


def _primary_worktree(cwd: Path) -> Path | None:
    worktrees = _run_git(cwd, "worktree", "list", "--porcelain", "-z")
    if worktrees.returncode != 0:
        return None
    first = next(
        (field for field in worktrees.stdout.split("\0") if field.startswith("worktree ")),
        "",
    )
    if not first:
        return None
    return Path(first.removeprefix("worktree ")).resolve()


def _emit(context: str) -> None:
    json.dump(
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            },
        },
        sys.stdout,
    )


def _start_mission_control(project_root: Path) -> None:
    if os.environ.get("CODEX_COORDINATOR_DISABLE_MISSION_CONTROL_AUTOSTART") == "1":
        return
    lifecycle = Path(__file__).with_name("mission_control_lifecycle.py")
    if not lifecycle.is_file():
        return
    command = [
        sys.executable,
        "-I",
        str(lifecycle),
        "start",
        "--automatic",
        "--project",
        str(project_root),
    ]
    options: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        options["start_new_session"] = True
    try:
        subprocess.Popen(command, **options)
    except OSError:
        return


def _marker_value(text: str, key: str) -> str | None:
    matches = re.findall(
        rf"(?mi)^\s*{re.escape(key)}\s*:\s*([^#\r\n]+?)\s*(?:#.*)?$",
        text,
    )
    if len(matches) != 1:
        return None
    return matches[0].strip().strip("`\"'")


def _emit_invalid_marker(project_id: str, warnings: list[str]) -> None:
    _emit(
        "\n".join(
            [
                "Codex Coordinator restart context (read-only; marker is incompatible):",
                f"project_id={project_id}",
                "state_warnings=" + ",".join(dict.fromkeys(warnings)),
                "Action: do not read project coordination state, accept coordination authority, or write Coordinator state until a user-authorised Maintainer repairs the marker.",
            ]
        )
    )


def _emit_internal_error(project_id: str) -> None:
    _emit(
        "\n".join(
            [
                "Codex Coordinator restart context (read-only; state could not be validated):",
                f"project_id={project_id}",
                "state_warnings=hook_internal_error",
                "Action: this hook grants no authority. Load the global codex-coordinator skill and inspect the canonical marker and state before coordinated work.",
            ]
        )
    )


def _sections(text: str, heading: str) -> list[str]:
    matches = list(
        re.finditer(rf"(?im)^##\s+{re.escape(heading)}\s*$", text)
    )
    sections: list[str] = []
    for match in matches:
        start = match.end()
        next_heading = re.search(r"(?im)^##\s+", text[start:])
        end = start + next_heading.start() if next_heading else len(text)
        sections.append(text[start:end])
    return sections


def _normalize_header(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.strip().strip("`").lower()))


def _split_table_row(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def _separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(cell and set(cell) <= {"-", ":", " "} for cell in cells)


def _parse_table(text: str, heading: str, slug: str) -> ParsedTable:
    sections = _sections(text, heading)
    if not sections:
        return ParsedTable([], False, [f"{slug}_section_missing"])
    if len(sections) != 1:
        return ParsedTable([], False, [f"{slug}_section_duplicate"])
    section = sections[0]
    table_lines = [line for line in section.splitlines() if line.lstrip().startswith("|")]
    if not table_lines:
        return ParsedTable([], False, [f"{slug}_table_missing"])

    raw_headers = _split_table_row(table_lines[0])
    normalized_headers = [_normalize_header(value) for value in raw_headers]
    schema = TABLE_SCHEMAS[slug]
    indexes: dict[str, int] = {}
    duplicate = False
    for canonical, aliases in schema.items():
        accepted = {_normalize_header(alias) for alias in aliases}
        matches = [index for index, value in enumerate(normalized_headers) if value in accepted]
        if len(matches) == 1:
            indexes[canonical] = matches[0]
        elif len(matches) > 1:
            duplicate = True

    warnings: list[str] = []
    accepted_headers = {
        _normalize_header(alias) for aliases in schema.values() for alias in aliases
    }
    if any(value not in accepted_headers for value in normalized_headers):
        warnings.append(f"{slug}_unknown_headers")
    if len(set(normalized_headers)) != len(normalized_headers):
        duplicate = True
    if duplicate:
        warnings.append(f"{slug}_duplicate_headers")
    if set(indexes) != set(schema):
        warnings.append(f"{slug}_required_headers_missing")
    if warnings:
        return ParsedTable([], False, warnings)

    rows: list[dict[str, str]] = []
    seen_rows: set[tuple[tuple[str, str], ...]] = set()
    seen_identities: set[str] = set()
    for line in table_lines[1:]:
        cells = _split_table_row(line)
        if _separator_row(cells):
            continue
        if len(cells) != len(raw_headers):
            warnings.append(f"{slug}_row_incomplete")
            continue
        values = {key: cells[index] for key, index in indexes.items()}
        if all(not value or value.upper() == "NONE" for value in values.values()):
            warnings.append(f"{slug}_row_empty")
            continue
        if not _valid_table_row(slug, values):
            warnings.append(f"{slug}_row_invalid")
        row_key = tuple(sorted(values.items()))
        if row_key in seen_rows:
            warnings.append(f"{slug}_duplicate_row")
        seen_rows.add(row_key)
        unique = _unique_row_identity(slug, values)
        if unique is not None:
            field, identity = unique
            if identity in seen_identities:
                warnings.append(f"{slug}_duplicate_{field}")
            seen_identities.add(identity)
        rows.append(values)
    return ParsedTable(rows, not warnings, warnings)


def _is_terminal_status(status: str) -> bool:
    return status == "UNKNOWN" or status.startswith(TERMINAL_PREFIXES)


def _is_pending_status(status: str) -> bool:
    return status != "NONE" and not status.startswith(TERMINAL_PREFIXES)


def _transition_ids(
    table: ParsedTable,
    *,
    current_session: Session | None,
    task_id: str,
    include_own: bool,
    reconcile_all: bool,
    current_truncated: bool,
    recipient_key: str | None,
) -> str:
    if current_truncated:
        return "UNKNOWN_TRUNCATED"
    if not table.valid:
        return "UNKNOWN_INVALID_STATE"
    items: list[str] = []
    for row in table.rows:
        if not reconcile_all:
            if not include_own:
                continue
            if recipient_key is not None:
                if current_session is None or not current_session.owns_address(
                    row[recipient_key]
                ):
                    continue
            elif task_id == "NONE" or _safe(row["task_id"], TOKEN) != task_id:
                continue
        task = _safe(row["task_id"], TOKEN)
        message = _safe(row["message_id"], TOKEN)
        status = _safe(row["status"], TOKEN)
        if "UNKNOWN" not in {task, message, status} and _is_pending_status(status):
            items.append(f"{task}:{message}:{status}")
    return ",".join(items) if items else "NONE"


def _excluded_task_ids(table: ParsedTable, *, current_truncated: bool) -> str:
    if current_truncated:
        return "UNKNOWN_TRUNCATED"
    if not table.valid:
        return "UNKNOWN_INVALID_STATE"
    items = [
        _safe(row["thread_id"], THREAD)
        for row in table.rows
        if _safe(row["status"], TOKEN) == "ACTIVE"
    ]
    return ",".join(item for item in items if item != "UNKNOWN") if items else "NONE"


def _active_task_warnings(
    active_table: ParsedTable,
    sessions: list[Session],
    *,
    coordinator_id: str,
    coordinator_name: str,
) -> list[str]:
    warnings: list[str] = []
    if not active_table.valid:
        return warnings
    for row in active_table.rows:
        task = _safe(row["task_id"], TOKEN)
        owner_address = row["owner"].strip().strip("`")
        expected_role = _safe(row["role"], TOKEN)
        task_status = _safe(row["status"], TOKEN)
        row_invalid = "UNKNOWN" in {task, expected_role, task_status}
        if row_invalid:
            warnings.append("active_task_row_invalid")

        owners = [session for session in sessions if session.owns_address(owner_address)]
        if not owners:
            warnings.extend(("active_task_owner_not_registered", "stale_active_task_binding"))
            continue
        if len(owners) > 1:
            warnings.extend(("active_task_owner_ambiguous", "stale_active_task_binding"))
            continue

        owner = owners[0]
        stale = row_invalid
        if owner.role != expected_role:
            warnings.append("active_task_owner_role_mismatch")
            stale = True
        if owner.task_id != task:
            warnings.append("active_task_owner_task_mismatch")
            stale = True
        if _is_terminal_status(owner.status):
            warnings.append("active_task_owner_terminal")
            stale = True
        if owner.accepts != "true":
            warnings.append("active_task_owner_not_accepting")
            stale = True
        if owner.scope_kind != "PROJECT_EXECUTION":
            warnings.append("active_task_owner_scope_mismatch")
            stale = True
        if _is_terminal_status(task_status):
            warnings.append("active_task_status_terminal")
            stale = True

        reusable_idle_coordinator = (
            owner.role == "COORDINATOR"
            and owner.task_id == "NONE"
            and owner.accepts == "true"
            and not _is_terminal_status(owner.status)
            and (owner.thread_id == coordinator_id or owner.thread_name == coordinator_name)
        )
        if reusable_idle_coordinator:
            warnings.append("active_task_bound_to_idle_coordinator")
            stale = True
        if stale:
            warnings.append("stale_active_task_binding")
    return warnings


def _reverse_task_warnings(active_table: ParsedTable, sessions: list[Session]) -> list[str]:
    if not active_table.valid:
        return []
    warnings: list[str] = []
    for session in sessions:
        if not (
            session.scope_kind == "PROJECT_EXECUTION"
            and session.accepts == "true"
            and session.task_id not in {"NONE", "UNKNOWN"}
            and not _is_terminal_status(session.status)
        ):
            continue
        matches = [
            row
            for row in active_table.rows
            if session.owns_address(row["owner"])
            and _safe(row["task_id"], TOKEN) == session.task_id
            and _safe(row["role"], TOKEN) == session.role
            and not _is_terminal_status(_safe(row["status"], TOKEN))
        ]
        if len(matches) != 1:
            warnings.extend(
                ("registered_task_missing_from_active_tasks", "stale_active_task_binding")
            )
    return warnings


def _coordinator_header_warnings(
    sessions: list[Session],
    *,
    coordinator_id: str,
    coordinator_name: str,
    coordinator_status: str,
    coordinator_accepts: str,
) -> list[str]:
    initial_unregistered = (
        coordinator_id == "NONE"
        and coordinator_name in {"NONE", "UNREGISTERED"}
        and coordinator_status == "UNREGISTERED"
        and coordinator_accepts == "false"
    )
    if initial_unregistered:
        live_coordinators = [
            session
            for session in sessions
            if session.role == "COORDINATOR"
            and session.scope_kind == "PROJECT_EXECUTION"
            and session.accepts == "true"
            and not _is_terminal_status(session.status)
        ]
        return (
            ["coordinator_header_not_unique", "stale_coordinator_binding"]
            if live_coordinators
            else []
        )

    if coordinator_id not in {"NONE", "UNAVAILABLE", "UNKNOWN"}:
        candidates = [
            session
            for session in sessions
            if session.thread_id == coordinator_id
            and session.thread_name == coordinator_name
        ]
    else:
        candidates = [
            session for session in sessions if session.thread_name == coordinator_name
        ]
    if len(candidates) != 1:
        return ["coordinator_header_not_unique", "stale_coordinator_binding"]

    coordinator = candidates[0]
    warnings: list[str] = []
    if coordinator.role != "COORDINATOR":
        warnings.append("coordinator_header_role_mismatch")
    if coordinator.scope_kind != "PROJECT_EXECUTION":
        warnings.append("coordinator_header_scope_mismatch")
    if _is_terminal_status(coordinator.status) or _is_terminal_status(coordinator_status):
        warnings.append("coordinator_header_terminal")
    if coordinator.accepts != "true" or coordinator_accepts != "true":
        warnings.append("coordinator_header_not_accepting")
    if coordinator.status != coordinator_status:
        warnings.append("coordinator_header_status_mismatch")
    if coordinator.accepts != coordinator_accepts:
        warnings.append("coordinator_header_acceptance_mismatch")
    if coordinator.task_id == "NONE" and coordinator.status != "IDLE":
        warnings.append("coordinator_without_task_not_idle")
    if coordinator.task_id not in {"NONE", "UNKNOWN"} and coordinator.status == "IDLE":
        warnings.append("coordinator_with_task_marked_idle")
    if warnings:
        warnings.append("stale_coordinator_binding")
    return warnings


def main() -> None:
    enabled_project_id: str | None = None
    try:
        payload = json.load(sys.stdin)
        cwd = Path(str(payload.get("cwd", "")))
        if not cwd.is_dir():
            return

        root = _primary_worktree(cwd)
        if root is None:
            return
        coordination = root / ".codex" / "coordination"
        marker_path = coordination / "project.yaml"
        if not marker_path.is_file():
            return

        marker = _read_bounded(marker_path, MARKER_LIMIT)
        enabled = _marker_value(marker.text, "coordination_enabled")
        if enabled is None:
            project_id = _safe(_marker_value(marker.text, "project_id") or "", PROJECT)
            _emit_invalid_marker(project_id, ["coordination_enabled_missing_or_invalid"])
            return
        if enabled.lower() == "false":
            return
        if enabled.lower() != "true":
            project_id = _safe(_marker_value(marker.text, "project_id") or "", PROJECT)
            _emit_invalid_marker(project_id, ["coordination_enabled_missing_or_invalid"])
            return

        project_raw = _marker_value(marker.text, "project_id") or ""
        project_id = _safe(project_raw, PROJECT)
        marker_warnings: list[str] = []
        if marker.truncated:
            marker_warnings.append("marker_truncated")
        if marker.invalid_utf8:
            marker_warnings.append("marker_invalid_utf8")
        if _marker_value(marker.text, "schema_version") != "1":
            marker_warnings.append("unsupported_marker_schema")
        if _marker_value(marker.text, "cross_project_task_access") != "false":
            marker_warnings.append("cross_project_task_access_not_false")
        if _marker_value(marker.text, "cross_project_state_changes") != "false":
            marker_warnings.append("cross_project_state_changes_not_false")
        if project_id == "UNKNOWN":
            marker_warnings.append("project_id_missing_or_invalid")
        if marker_warnings:
            _emit_invalid_marker(project_id, marker_warnings)
            return
        enabled_project_id = project_id
        _start_mission_control(root)

        current_path = coordination / "CURRENT.md"
        if current_path.exists() and not current_path.is_file():
            raise OSError("CURRENT.md is not a regular file")
        if current_path.is_file():
            current = _read_bounded(current_path, CURRENT_LIMIT)
        else:
            current = BoundedText("", False, False)

        warnings: list[str] = []
        if not current_path.is_file():
            warnings.append("current_state_missing")
        if current.truncated:
            warnings.append("current_state_truncated")
        if current.invalid_utf8:
            warnings.append("current_state_invalid_utf8")

        current_project_id = _required_field(
            current.text,
            "Project ID",
            PROJECT,
            "UNKNOWN",
        )
        if current_project_id != project_id:
            warning = (
                "project_id_mismatch"
                if current_project_id != "UNKNOWN"
                else "current_project_id_missing_or_invalid"
            )
            warnings.append(warning)
            _emit(
                "\n".join(
                    [
                        "Codex Coordinator restart context (read-only; state is invalid):",
                        f"project_id={project_id}",
                        "state_warnings=" + ",".join(dict.fromkeys(warnings)),
                        "Action: do not accept coordination authority or write Coordinator state until a user-authorised Maintainer repairs it.",
                    ]
                )
            )
            return

        epoch = _required_field(current.text, "Coordination epoch", EPOCH, "UNKNOWN")
        mode = _required_field(current.text, "Coordination mode", TOKEN, "UNKNOWN")
        shared_goal = _required_field(
            current.text,
            "Shared goal",
            SHARED_GOAL,
            "UNKNOWN",
        )
        if shared_goal != "UNKNOWN":
            shared_goal = _normalize_shared_goal(shared_goal)
        last_reconciliation = _required_field(
            current.text,
            "Last reconciliation",
            RECONCILIATION,
            "UNKNOWN",
        )
        coordinator_id = _required_field(
            current.text,
            "Coordinator thread ID",
            THREAD,
            "UNKNOWN",
        )
        coordinator_name = _required_field(
            current.text,
            "Coordinator thread name",
            NAME,
            "UNKNOWN",
        )
        coordinator_status = _required_field(
            current.text,
            "Coordinator status",
            TOKEN,
            "UNKNOWN",
        )
        coordinator_accepts = _required_field(
            current.text,
            "Accepts project messages",
            BOOL,
            "UNKNOWN",
        )

        for label, value in (
            ("coordination_epoch_missing_or_invalid", epoch),
            ("coordination_mode_missing_or_invalid", mode),
            ("shared_goal_missing_or_invalid", shared_goal),
            ("last_reconciliation_missing_or_invalid", last_reconciliation),
            ("coordinator_thread_id_missing_or_invalid", coordinator_id),
            ("coordinator_thread_name_missing_or_invalid", coordinator_name),
            ("coordinator_status_missing_or_invalid", coordinator_status),
            ("coordinator_acceptance_missing_or_invalid", coordinator_accepts),
        ):
            if value == "UNKNOWN":
                warnings.append(label)

        if mode not in {"MANAGING", "REPORT_ONLY", "ATTENTION_NEEDED", "UNKNOWN"}:
            warnings.append("legacy_or_invalid_coordination_mode")

        registered_table = _parse_table(current.text, "Registered sessions", "registered_sessions")
        active_table = _parse_table(current.text, "Active tasks", "active_tasks")
        pending_table = _parse_table(current.text, "Pending commands", "pending_commands")
        paused_table = _parse_table(current.text, "Paused work", "paused_work")
        resume_table = _parse_table(current.text, "Resume queue", "resume_queue")
        blocked_table = _parse_table(current.text, "Blocked decisions", "blocked_decisions")
        excluded_table = _parse_table(current.text, "Excluded tasks", "excluded_tasks")
        for table in (
            registered_table,
            active_table,
            pending_table,
            paused_table,
            resume_table,
            blocked_table,
            excluded_table,
        ):
            warnings.extend(table.warnings)
        if not active_table.valid:
            warnings.append("stale_active_task_binding")

        sessions: list[Session] = []
        fallback_names: set[str] = set()
        if registered_table.valid:
            for row in registered_table.rows:
                session = Session(
                    thread_id=_safe(row["thread_id"], THREAD),
                    thread_name=_safe(row["thread_name"], NAME),
                    scope_kind=_safe(row["scope_kind"], TOKEN),
                    role=_safe(row["role"], TOKEN),
                    task_id=_safe(_normalize_taskless(row["task_id"]), TOKEN),
                    status=_safe(row["status"], TOKEN),
                    accepts=_safe(row["accepts"], BOOL),
                )
                if "UNKNOWN" in {
                    session.thread_id,
                    session.thread_name,
                    session.scope_kind,
                    session.role,
                    session.task_id,
                    session.status,
                    session.accepts,
                }:
                    warnings.append("registered_session_row_invalid")
                if (
                    session.thread_id in {"NONE", "UNAVAILABLE"}
                    and session.thread_name != "UNKNOWN"
                    and session.accepts == "true"
                ):
                    if session.thread_name in fallback_names:
                        warnings.append("duplicate_fallback_session_name")
                    fallback_names.add(session.thread_name)
                sessions.append(session)

        warnings.extend(
            _active_task_warnings(
                active_table,
                sessions,
                coordinator_id=coordinator_id,
                coordinator_name=coordinator_name,
            )
        )
        warnings.extend(_reverse_task_warnings(active_table, sessions))
        warnings.extend(
            _coordinator_header_warnings(
                sessions,
                coordinator_id=coordinator_id,
                coordinator_name=coordinator_name,
                coordinator_status=coordinator_status,
                coordinator_accepts=coordinator_accepts,
            )
        )
        if coordinator_id == "NONE" or coordinator_status == "UNREGISTERED" or coordinator_accepts != "true":
            warnings.append("enabled_project_coordinator_not_active")

        session_id = _safe(str(payload.get("session_id", "")), THREAD)
        if session_id == "UNKNOWN":
            warnings.append("this_session_id_missing_or_invalid")
        scope_kind = "UNREGISTERED"
        role = "UNREGISTERED"
        task_id = "NONE"
        session_accepts = "false"
        current_session: Session | None = None
        for session in sessions:
            if session.thread_id != session_id:
                continue
            scope_kind = session.scope_kind
            role = session.role
            task_id = session.task_id
            session_accepts = session.accepts
            current_session = session
            break

        reconcile_all = (
            role == "COORDINATOR"
            and scope_kind == "PROJECT_EXECUTION"
            and session_accepts == "true"
        )
        include_own = scope_kind == "PROJECT_EXECUTION" and session_accepts == "true"

        context = "\n".join(
            [
                "Codex Coordinator restart context (read-only; documents remain authoritative):",
                f"project_id={project_id}",
                f"coordination_epoch={epoch}",
                f"coordination_mode={mode}",
                f"shared_goal={shared_goal}",
                f"last_reconciliation={last_reconciliation}",
                f"coordinator_thread_id={coordinator_id}",
                f"coordinator_thread_name={coordinator_name}",
                f"coordinator_status={coordinator_status}",
                f"coordinator_accepts_project_messages={coordinator_accepts}",
                "excluded_tasks=" + _excluded_task_ids(excluded_table, current_truncated=current.truncated),
                f"this_session_id={session_id}",
                f"registered_scope_kind={scope_kind}",
                f"registered_role={role}",
                f"assigned_task_id={task_id}",
                f"this_session_accepts_project_messages={session_accepts}",
                "state_warnings=" + (",".join(dict.fromkeys(warnings)) if warnings else "NONE"),
                "pending_commands="
                + _transition_ids(
                    pending_table,
                    current_session=current_session,
                    task_id=task_id,
                    include_own=include_own,
                    reconcile_all=reconcile_all,
                    current_truncated=current.truncated,
                    recipient_key="recipient",
                ),
                "pending_resume_actions="
                + _transition_ids(
                    resume_table,
                    current_session=current_session,
                    task_id=task_id,
                    include_own=include_own,
                    reconcile_all=reconcile_all,
                    current_truncated=current.truncated,
                    recipient_key=None,
                ),
                "Load the latest global codex-coordinator skill and its applicable lane from disk before any coordinated action; do not rely on instructions retained from an earlier turn.",
                "Before substantial project writes, read project.yaml, CURRENT.md, and the assigned task. This hook never grants ownership.",
            ]
        )
        _emit(context)
    except Exception:
        if enabled_project_id is not None:
            try:
                _emit_internal_error(enabled_project_id)
            except Exception:
                return


if __name__ == "__main__":
    main()
