#!/usr/bin/env python3
"""Deterministic helpers for local Codex Coordinator state files."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
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
    if label == "Shared goal" and not 1 <= len(value) <= 512:
        raise StateError("Invalid required 'Shared goal' field")
    if label == "Last reconciliation" and not _valid_reconciliation(value):
        raise StateError("Invalid required 'Last reconciliation' field")
    if label == "Coordinator thread name" and not (
        1 <= len(value) <= 120 and "|" not in value
    ):
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

    text = path.read_text(encoding="utf-8")
    shared_matches = _field_matches(text, "Shared goal")
    shared_value = shared_matches[0].group(1).strip()
    if shared_value.lower() in NO_ACTIVE_GOAL and shared_value != "none":
        text = (
            text[: shared_matches[0].start()]
            + "**Shared goal:** none"
            + text[shared_matches[0].end() :]
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
                ending = "\n" if lines[line_index].endswith("\n") else ""
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

    table_lines = [line for line in text.splitlines() if line.lstrip().startswith("|")]
    if len(table_lines) < 3:
        raise StateError("Reconciliation ledger is missing")
    headers = _split_row(table_lines[0])
    if tuple(headers) != LEDGER_HEADER:
        raise StateError("Reconciliation ledger header is invalid")
    rows = []
    for line in table_lines[1:]:
        cells = _split_row(line)
        if _separator(cells):
            continue
        if len(cells) != len(headers):
            raise StateError("Reconciliation ledger contains an incomplete row")
        if cells[2] not in LEDGER_STATUSES:
            raise StateError(f"Unknown reconciliation status: {cells[2]}")
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

    args = parser.parse_args(argv)
    try:
        if args.command == "validate-current":
            report = normalize_current(args.path) if args.write_normalized else validate_current(args.path)
        elif args.command == "validate-reconciliation":
            report = validate_reconciliation(args.path)
        else:
            content = args.content_file.read_bytes() if args.content_file else sys.stdin.buffer.read()
            report = create_file(args.coordination_root, args.relative_path, content)
    except (OSError, UnicodeError, StateError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, indent=2))
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
