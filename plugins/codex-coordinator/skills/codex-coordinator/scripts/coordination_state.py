#!/usr/bin/env python3
"""Deterministic helpers for local Codex Coordinator state files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "Project ID",
    "Coordination epoch",
    "Coordination mode",
    "Shared goal",
    "Last reconciliation",
    "Coordinator thread ID",
    "Coordinator thread name",
    "Coordinator status",
    "Accepts project messages",
)

TABLES: dict[str, tuple[str, ...]] = {
    "Registered sessions": (
        "Thread ID",
        "Thread name",
        "Scope kind",
        "Role",
        "Task ID",
        "Status",
        "Accepts project messages",
    ),
    "Active tasks": ("Task ID", "Owner", "Role", "Status"),
    "Pending commands": (
        "Task ID",
        "Message ID",
        "Recipient thread ID",
        "Message type",
        "Status",
    ),
    "Paused work": ("Task ID", "Owner", "Reason", "Resume condition", "Status"),
    "Resume queue": ("Task ID", "Message ID", "Resume condition", "Status"),
    "Blocked decisions": ("Decision ID", "Task ID", "Decision needed", "Status"),
}

TASKLESS = {"", "-", "none", "n/a", "not applicable"}
NO_ACTIVE_GOAL = TASKLESS | {"no active coordinated goal", "no active coordinated goal."}
RECONCILIATION_FIELDS = (
    "type",
    "project_id",
    "coordination_epoch",
    "message_id",
    "reported_by_thread",
    "related_task_id",
    "state",
)
LEDGER_HEADER = (
    "Task or promise",
    "Relationship to shared goal",
    "Status",
    "Evidence or remaining work",
    "Recommended disposition",
)
LEDGER_STATUSES = {
    "DONE",
    "REMAINS_IN_CURRENT_TASK",
    "DEPENDENT_TASK",
    "NEEDS_USER_APPROVAL",
    "BLOCKED",
    "NOT_NEEDED",
}
PROJECT = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
TOKEN = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,63}")
THREAD = re.compile(
    r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|NONE|UNAVAILABLE)"
)
EPOCH = re.compile(r"\d{1,9}")
BOOL = re.compile(r"(?:true|false)")
SHA256 = re.compile(r"[0-9a-f]{64}")
CACHE_SCHEMA_VERSION = 1
MAX_INBOX_RECORD_BYTES = 4 * 1024 * 1024


class StateError(RuntimeError):
    pass


def _normalize_header(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.strip().strip("`").lower()))


def _split_row(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def _separator(cells: list[str]) -> bool:
    return bool(cells) and all(cell and set(cell) <= {"-", ":", " "} for cell in cells)


def _field_matches(text: str, label: str) -> list[re.Match[str]]:
    return list(
        re.finditer(
            rf"(?m)^\s*\*\*{re.escape(label)}:\*\*\s*`?([^`\r\n]*)`?\s*$",
            text,
        )
    )


def _valid_reconciliation(value: str) -> bool:
    if not 1 <= len(value) <= 64 or "T" not in value:
        return False
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(candidate).utcoffset() is not None
    except ValueError:
        return False


def _valid_text(value: str, *, maximum: int) -> bool:
    return (
        1 <= len(value) <= maximum
        and "|" not in value
        and not any(
            character in {"\r", "\n", "\u2028", "\u2029"}
            or unicodedata.category(character) in {"Cc", "Cs"}
            for character in value
        )
    )


def _valid_address(value: str) -> bool:
    if THREAD.fullmatch(value):
        return value not in {"NONE", "UNAVAILABLE"}
    return _valid_text(value, maximum=120)


def _validate_required_field(label: str, value: str) -> None:
    patterns = {
        "Project ID": PROJECT,
        "Coordination epoch": EPOCH,
        "Coordination mode": TOKEN,
        "Coordinator thread ID": THREAD,
        "Coordinator status": TOKEN,
        "Accepts project messages": BOOL,
    }
    pattern = patterns.get(label)
    if pattern is not None and not pattern.fullmatch(value):
        raise StateError(f"Invalid required {label!r} field")
    if label == "Shared goal" and not _valid_text(value, maximum=512):
        raise StateError("Invalid required 'Shared goal' field")
    if label == "Last reconciliation" and not _valid_reconciliation(value):
        raise StateError("Invalid required 'Last reconciliation' field")
    if label == "Coordinator thread name" and not _valid_text(value, maximum=120):
        raise StateError("Invalid required 'Coordinator thread name' field")


def _section(text: str, heading: str) -> tuple[str, int, int]:
    matches = list(re.finditer(rf"(?im)^##\s+{re.escape(heading)}\s*$", text))
    if len(matches) != 1:
        raise StateError(f"Expected exactly one {heading!r} section, found {len(matches)}")
    start = matches[0].end()
    next_heading = re.search(r"(?im)^##\s+", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end], start, end


def _table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    section, _, _ = _section(text, heading)
    lines = [line for line in section.splitlines() if line.lstrip().startswith("|")]
    if len(lines) < 2:
        raise StateError(f"{heading!r} must retain its table header and separator")
    headers = _split_row(lines[0])
    normalized = [_normalize_header(value) for value in headers]
    required = [_normalize_header(value) for value in TABLES[heading]]
    if len(set(normalized)) != len(normalized) or set(normalized) != set(required):
        raise StateError(f"{heading!r} has missing, duplicate, or unknown columns")
    rows: list[list[str]] = []
    for line in lines[1:]:
        cells = _split_row(line)
        if _separator(cells):
            continue
        if len(cells) != len(headers):
            raise StateError(f"{heading!r} contains an incomplete row")
        rows.append(cells)
    return headers, rows


def _validate_table_rows(heading: str, headers: list[str], rows: list[list[str]]) -> None:
    indexes = {_normalize_header(value): index for index, value in enumerate(headers)}

    def cell(row: list[str], column: str) -> str:
        return row[indexes[_normalize_header(column)]]

    def token(value: str) -> bool:
        return bool(TOKEN.fullmatch(value))

    validators: dict[str, dict[str, Any]] = {
        "Registered sessions": {
            "Thread ID": lambda value: bool(THREAD.fullmatch(value)),
            "Thread name": lambda value: _valid_text(value, maximum=120),
            "Scope kind": token,
            "Role": token,
            "Task ID": lambda value: value.strip().lower() in TASKLESS or token(value),
            "Status": token,
            "Accepts project messages": lambda value: bool(BOOL.fullmatch(value)),
        },
        "Active tasks": {
            "Task ID": token,
            "Owner": _valid_address,
            "Role": token,
            "Status": token,
        },
        "Pending commands": {
            "Task ID": token,
            "Message ID": token,
            "Recipient thread ID": _valid_address,
            "Message type": token,
            "Status": token,
        },
        "Paused work": {
            "Task ID": token,
            "Owner": _valid_address,
            "Reason": lambda value: _valid_text(value, maximum=512),
            "Resume condition": lambda value: _valid_text(value, maximum=512),
            "Status": token,
        },
        "Resume queue": {
            "Task ID": token,
            "Message ID": token,
            "Resume condition": lambda value: _valid_text(value, maximum=512),
            "Status": token,
        },
        "Blocked decisions": {
            "Decision ID": token,
            "Task ID": token,
            "Decision needed": lambda value: _valid_text(value, maximum=512),
            "Status": token,
        },
    }
    unique_columns = {
        "Active tasks": "Task ID",
        "Pending commands": "Message ID",
        "Paused work": "Task ID",
        "Resume queue": "Message ID",
        "Blocked decisions": "Decision ID",
    }
    seen_rows: set[tuple[str, ...]] = set()
    seen_keys: set[str] = set()
    for row in rows:
        row_key = tuple(row)
        if row_key in seen_rows:
            raise StateError(f"{heading!r} contains a duplicate row")
        seen_rows.add(row_key)
        for column, validator in validators[heading].items():
            value = cell(row, column)
            if not validator(value):
                raise StateError(f"{heading!r} contains an invalid {column!r} value")

        if heading == "Registered sessions":
            thread_id = cell(row, "Thread ID")
            unique_key = thread_id if thread_id not in {"NONE", "UNAVAILABLE"} else cell(
                row, "Thread name"
            )
        elif heading in unique_columns:
            unique_key = cell(row, unique_columns[heading])
        else:
            continue
        if unique_key in seen_keys:
            raise StateError(f"{heading!r} contains a duplicate identity: {unique_key}")
        seen_keys.add(unique_key)


def validate_current(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise StateError(f"Cannot read {path}: {error}") from error

    fields: dict[str, str] = {}
    normalizations: list[dict[str, str]] = []
    for label in REQUIRED_FIELDS:
        matches = _field_matches(text, label)
        if len(matches) != 1:
            raise StateError(f"Expected exactly one {label!r} field, found {len(matches)}")
        fields[label] = matches[0].group(1).strip()
        _validate_required_field(label, fields[label])

    if fields["Shared goal"].strip().lower() in NO_ACTIVE_GOAL:
        if fields["Shared goal"] != "none":
            normalizations.append(
                {"field": "Shared goal", "from": fields["Shared goal"], "to": "none"}
            )
        fields["Shared goal"] = "none"

    tables: dict[str, int] = {}
    for heading in TABLES:
        headers, rows = _table(text, heading)
        _validate_table_rows(heading, headers, rows)
        tables[heading] = len(rows)
        if heading != "Registered sessions":
            continue
        task_index = [_normalize_header(value) for value in headers].index("task id")
        for index, row in enumerate(rows, start=1):
            if row[task_index].strip().lower() in TASKLESS and row[task_index] != "NONE":
                normalizations.append(
                    {
                        "section": heading,
                        "row": str(index),
                        "column": "Task ID",
                        "from": row[task_index],
                        "to": "NONE",
                    }
                )

    return {
        "status": "valid",
        "path": str(path.resolve(strict=False)),
        "fields": fields,
        "tableRows": tables,
        "normalizations": normalizations,
    }


def normalize_current(path: Path) -> dict[str, Any]:
    report = validate_current(path)
    if not report["normalizations"]:
        report["status"] = "current"
        return report

    with path.open("r", encoding="utf-8", newline="") as stream:
        text = stream.read()
    shared_matches = _field_matches(text, "Shared goal")
    shared_value = shared_matches[0].group(1).strip()
    if shared_value.lower() in NO_ACTIVE_GOAL and shared_value != "none":
        text = (
            text[: shared_matches[0].start(1)]
            + "none"
            + text[shared_matches[0].end(1) :]
        )

    section, start, end = _section(text, "Registered sessions")
    lines = section.splitlines(keepends=True)
    table_indexes = [index for index, line in enumerate(lines) if line.lstrip().startswith("|")]
    if table_indexes:
        headers = _split_row(lines[table_indexes[0]])
        task_index = [_normalize_header(value) for value in headers].index("task id")
        for line_index in table_indexes[1:]:
            cells = _split_row(lines[line_index])
            if _separator(cells) or len(cells) != len(headers):
                continue
            if cells[task_index].strip().lower() in TASKLESS:
                cells[task_index] = "NONE"
                ending = (
                    "\r\n"
                    if lines[line_index].endswith("\r\n")
                    else ("\n" if lines[line_index].endswith("\n") else "")
                )
                lines[line_index] = "| " + " | ".join(cells) + " |" + ending
    text = text[:start] + "".join(lines) + text[end:]
    _atomic_replace(path, text.encode("utf-8"))
    updated = validate_current(path)
    updated["status"] = "normalized"
    return updated


def validate_reconciliation(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise StateError(f"Cannot read {path}: {error}") from error

    values: dict[str, str] = {}
    for key in RECONCILIATION_FIELDS:
        matches = re.findall(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", text)
        if len(matches) != 1 or not matches[0]:
            raise StateError(f"Expected exactly one non-empty {key!r} field")
        values[key] = matches[0]
    if values["type"] != "TURN_RECONCILIATION":
        raise StateError("Record is not a TURN_RECONCILIATION")
    if not PROJECT.fullmatch(values["project_id"]):
        raise StateError("Invalid reconciliation project_id")
    if not EPOCH.fullmatch(values["coordination_epoch"]):
        raise StateError("Invalid reconciliation coordination_epoch")
    if values["state"] != "REPORTING":
        raise StateError("Invalid reconciliation state; expected REPORTING")
    if not TOKEN.fullmatch(values["message_id"]):
        raise StateError("Invalid reconciliation message_id")
    if not _valid_address(values["reported_by_thread"]):
        raise StateError("Invalid reconciliation reported_by_thread")
    if not TOKEN.fullmatch(values["related_task_id"]):
        raise StateError("Invalid reconciliation related_task_id")

    table_lines = [line for line in text.splitlines() if line.lstrip().startswith("|")]
    if len(table_lines) < 3:
        raise StateError("Reconciliation ledger is missing")
    headers = _split_row(table_lines[0])
    if tuple(headers) != LEDGER_HEADER:
        raise StateError("Reconciliation ledger header is invalid")
    rows = []
    seen_rows: set[tuple[str, ...]] = set()
    for line in table_lines[1:]:
        cells = _split_row(line)
        if _separator(cells):
            continue
        if len(cells) != len(headers):
            raise StateError("Reconciliation ledger contains an incomplete row")
        if any(not _valid_text(cell, maximum=4096) for cell in cells):
            raise StateError("Reconciliation ledger contains an empty or invalid cell")
        if cells[2] not in LEDGER_STATUSES:
            raise StateError(f"Unknown reconciliation status: {cells[2]}")
        row_key = tuple(cells)
        if row_key in seen_rows:
            raise StateError("Reconciliation ledger contains a duplicate row")
        seen_rows.add(row_key)
        rows.append(dict(zip(headers, cells, strict=True)))
    if not rows:
        raise StateError("Reconciliation ledger has no rows")
    return {
        "status": "valid",
        "path": str(path.resolve(strict=False)),
        "record": values,
        "ledgerRows": rows,
    }


def _atomic_replace(path: Path, data: bytes) -> None:
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        Path(temporary_name).replace(path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def _inbox_scope(project_id: str, coordination_epoch: int, coordinator_id: str) -> dict[str, Any]:
    if not PROJECT.fullmatch(project_id):
        raise StateError("Invalid inbox-cache project ID")
    if coordination_epoch < 0 or coordination_epoch > 999_999_999:
        raise StateError("Invalid inbox-cache coordination epoch")
    if not THREAD.fullmatch(coordinator_id) or coordinator_id in {"NONE", "UNAVAILABLE"}:
        raise StateError("Invalid inbox-cache Coordinator thread ID")
    return {
        "projectId": project_id,
        "coordinationEpoch": coordination_epoch,
        "coordinatorThreadId": coordinator_id,
    }


def _hash_inbox_file(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    if size > MAX_INBOX_RECORD_BYTES:
        raise StateError(
            f"Inbox record exceeds the {MAX_INBOX_RECORD_BYTES}-byte checkpoint limit: {path.name}"
        )
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _inbox_files(root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    inbox = root / "inbox"
    if not inbox.exists():
        return {}, []
    if not inbox.is_dir() or inbox.is_symlink():
        raise StateError("Coordination inbox must be a real directory")

    files: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for path in sorted(inbox.iterdir(), key=lambda value: value.name.lower()):
        if path.suffix.lower() != ".md":
            continue
        if path.is_symlink():
            warnings.append(f"unsafe_symlink:{path.name}")
            continue
        if not path.is_file():
            warnings.append(f"unsafe_non_file:{path.name}")
            continue
        try:
            files[path.name] = _hash_inbox_file(path)
        except (OSError, StateError) as error:
            warnings.append(f"unreadable:{path.name}:{error}")
    return files, warnings


def _load_inbox_index(
    path: Path, scope: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], str]:
    if not path.exists():
        return {}, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schemaVersion") != CACHE_SCHEMA_VERSION:
            return {}, "outdated"
        if value.get("scope") != scope:
            return {}, "scope_changed"
        acknowledged = value.get("acknowledged")
        if not isinstance(acknowledged, dict):
            return {}, "corrupt"
        validated: dict[str, dict[str, Any]] = {}
        for name, record in acknowledged.items():
            if (
                not isinstance(name, str)
                or Path(name).name != name
                or not name.lower().endswith(".md")
                or not isinstance(record, dict)
                or not SHA256.fullmatch(str(record.get("sha256", "")))
                or not isinstance(record.get("bytes"), int)
                or record["bytes"] < 0
                or record["bytes"] > MAX_INBOX_RECORD_BYTES
            ):
                return {}, "corrupt"
            validated[name] = {
                "sha256": record["sha256"],
                "bytes": record["bytes"],
            }
        return validated, "current"
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}, "corrupt"


def scan_inbox(
    root: Path,
    *,
    project_id: str,
    coordination_epoch: int,
    coordinator_id: str,
) -> dict[str, Any]:
    """Return unacknowledged inbox records without advancing the checkpoint."""
    root = root.resolve(strict=False)
    scope = _inbox_scope(project_id, coordination_epoch, coordinator_id)
    cache_path = root / "cache" / "inbox-index.json"
    acknowledged, cache_status = _load_inbox_index(cache_path, scope)
    current, warnings = _inbox_files(root)

    pending: list[dict[str, Any]] = []
    acknowledged_count = 0
    for name, record in current.items():
        previous = acknowledged.get(name)
        if previous == record:
            acknowledged_count += 1
            continue
        reason = "changed" if previous is not None else "new"
        pending.append({"path": f"inbox/{name}", **record, "reason": reason})
        if reason == "changed":
            warnings.append(f"acknowledged_record_changed:{name}")

    stale = sorted(name for name in acknowledged if name not in current)
    warnings.extend(f"acknowledged_record_missing:{name}" for name in stale)
    return {
        "status": "pending" if pending or warnings else "current",
        "cacheStatus": cache_status,
        "cachePath": str(cache_path),
        "pendingRecords": pending,
        "acknowledgedCount": acknowledged_count,
        "staleAcknowledgements": [f"inbox/{name}" for name in stale],
        "warnings": warnings,
    }


def _parse_acknowledgements(values: list[str]) -> dict[str, str]:
    records: dict[str, str] = {}
    for value in values:
        relative, separator, digest = value.rpartition("=")
        path = Path(relative)
        if (
            not separator
            or path.is_absolute()
            or path.parts[:1] != ("inbox",)
            or len(path.parts) != 2
            or path.suffix.lower() != ".md"
            or ".." in path.parts
            or not SHA256.fullmatch(digest)
        ):
            raise StateError("Acknowledgement must be inbox/<record>.md=<sha256>")
        if path.name in records:
            raise StateError(f"Duplicate inbox acknowledgement: {path.name}")
        records[path.name] = digest
    return records


def acknowledge_inbox(
    root: Path,
    *,
    project_id: str,
    coordination_epoch: int,
    coordinator_id: str,
    records: dict[str, str],
) -> dict[str, Any]:
    """Advance checkpoints only for exact record hashes already reconciled by the caller."""
    if not records:
        raise StateError("At least one inbox record acknowledgement is required")
    root = root.resolve(strict=False)
    scope = _inbox_scope(project_id, coordination_epoch, coordinator_id)
    cache_path = root / "cache" / "inbox-index.json"
    acknowledged, cache_status = _load_inbox_index(cache_path, scope)
    current, warnings = _inbox_files(root)
    if warnings:
        raise StateError("Cannot advance inbox checkpoint while inbox scan warnings exist")

    for name, expected_digest in records.items():
        current_record = current.get(name)
        if current_record is None:
            raise StateError(f"Inbox record is missing or unsafe: {name}")
        if current_record["sha256"] != expected_digest:
            raise StateError(f"Inbox record changed before acknowledgement: {name}")

    acknowledged = {
        name: record for name, record in acknowledged.items() if name in current
    }
    for name in records:
        acknowledged[name] = current[name]
    payload = {
        "schemaVersion": CACHE_SCHEMA_VERSION,
        "scope": scope,
        "acknowledged": dict(sorted(acknowledged.items())),
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_replace(
        cache_path,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return {
        "status": "acknowledged",
        "cacheStatus": cache_status,
        "cachePath": str(cache_path),
        "acknowledgedRecords": [f"inbox/{name}" for name in sorted(records)],
        "acknowledgedCount": len(acknowledged),
    }


def create_file(root: Path, relative: Path, content: bytes) -> dict[str, Any]:
    root = root.resolve(strict=False)
    if relative.is_absolute() or relative.suffix.lower() != ".md":
        raise StateError("Relative path must be a Markdown file")
    if (
        not relative.parts
        or relative.parts[0] not in {"tasks", "inbox"}
        or ".." in relative.parts
    ):
        raise StateError("File must be created under tasks/ or inbox/")
    target = (root / relative).resolve(strict=False)
    try:
        normalized_relative = target.relative_to(root)
    except ValueError as error:
        raise StateError("Target escapes the coordination root") from error
    if not normalized_relative.parts or normalized_relative.parts[0] not in {"tasks", "inbox"}:
        raise StateError("Target escapes the task and inbox record directories")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise StateError(f"Refusing to overwrite existing record: {target}") from error
    return {"status": "created", "path": str(target), "bytes": len(content)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-current")
    validate.add_argument("path", type=Path)
    validate.add_argument("--write-normalized", action="store_true")

    reconciliation = commands.add_parser("validate-reconciliation")
    reconciliation.add_argument("path", type=Path)

    create = commands.add_parser("create-file")
    create.add_argument("--coordination-root", required=True, type=Path)
    create.add_argument("--relative-path", required=True, type=Path)
    create.add_argument("--content-file", type=Path)

    scan = commands.add_parser("scan-inbox")
    scan.add_argument("--coordination-root", required=True, type=Path)
    scan.add_argument("--project-id", required=True)
    scan.add_argument("--coordination-epoch", required=True, type=int)
    scan.add_argument("--coordinator-id", required=True)

    acknowledge = commands.add_parser("ack-inbox")
    acknowledge.add_argument("--coordination-root", required=True, type=Path)
    acknowledge.add_argument("--project-id", required=True)
    acknowledge.add_argument("--coordination-epoch", required=True, type=int)
    acknowledge.add_argument("--coordinator-id", required=True)
    acknowledge.add_argument("--record", action="append", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "validate-current":
            report = normalize_current(args.path) if args.write_normalized else validate_current(args.path)
        elif args.command == "validate-reconciliation":
            report = validate_reconciliation(args.path)
        elif args.command == "create-file":
            content = args.content_file.read_bytes() if args.content_file else sys.stdin.buffer.read()
            report = create_file(args.coordination_root, args.relative_path, content)
        elif args.command == "scan-inbox":
            report = scan_inbox(
                args.coordination_root,
                project_id=args.project_id,
                coordination_epoch=args.coordination_epoch,
                coordinator_id=args.coordinator_id,
            )
        else:
            report = acknowledge_inbox(
                args.coordination_root,
                project_id=args.project_id,
                coordination_epoch=args.coordination_epoch,
                coordinator_id=args.coordinator_id,
                records=_parse_acknowledgements(args.record),
            )
    except (OSError, UnicodeError, StateError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, indent=2))
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
