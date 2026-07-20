from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


MAX_MARKER_BYTES = 64 * 1024
MAX_TASK_HEADER_BYTES = 96 * 1024
MAX_INBOX_HEADER_BYTES = 8 * 1024
MAX_ROLLOUT_TAIL_BYTES = 64 * 1024
MAX_AUTOMATION_BYTES = 256 * 1024
PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
THREAD_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
TERMINAL_STATUS = re.compile(
    r"^(?:COMPLETE|COMPLETED|DONE|TERMINAL|RELEASED|SUPERSEDED|ARCHIVED|CANCELLED|CANCELED|FAILED)"
)
ACTIVE_COORDINATION_MODES = {"MANAGING", "REPORT_ONLY", "ATTENTION_NEEDED"}
WORKER_ROLES = {"TASK_AGENT", "ADVISER", "REVIEWER", "WORKER"}
REVIEW_ONLY_CHECKS = (
    "worker-semantic-granularity",
    "thread-goal-semantic-match",
)
MAX_SEMANTIC_REVIEW_TASKS = 12
MAX_SEMANTIC_PACKET_BYTES = 12 * 1024


def _read_bounded(path: Path, limit: int) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except (OSError, ValueError):
        return b""
    return data if len(data) <= limit else b""


def _simple_yaml(data: bytes) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in data.splitlines():
        match = re.match(rb"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$", raw)
        if match:
            values[match.group(1).decode("ascii")] = match.group(2).decode(
                "utf-8", errors="replace"
            ).strip("\"'")
    return values


def _normalized_key(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _clean_value(value: str) -> str:
    return value.strip().strip("`\"'").strip()


def _semantic_text(value: Any, limit: int) -> str:
    """Bound and scrub contract text before an opt-in model review."""
    text = str(value or "")
    text = THREAD_ID.sub("[task]", text)
    text = re.sub(r"(?i)\b(?:https?|file)://\S+", "[link]", text)
    text = re.sub(r"(?i)(?:[A-Z]:[\\/]|\\\\)[^\s`\"']+", "[path]", text)
    text = re.sub(r"(?<!\w)/(?:[^\s/]+/)+[^\s`\"']*", "[path]", text)
    text = re.sub(
        r"(?<![\w-])(?:[\w.-]+[\\/])+(?:[\w.-]+)(?![\w-])", "[path]", text
    )
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:")
    if len(text) > limit:
        return text[: max(1, limit - 1)].rstrip() + "…"
    return text


def _task_contract(path: Path) -> tuple[dict[str, str], list[str]]:
    data = _read_bounded(path, MAX_TASK_HEADER_BYTES)
    if not data:
        return {}, []
    text = data.decode("utf-8", errors="replace")
    text = re.split(
        r"(?im)^##\s+(?:History|Transition log|Reconciliation notes)\s*$",
        text,
        maxsplit=1,
    )[0]
    fields: dict[str, str] = {}
    paths: list[str] = []
    list_key = ""
    for line in text.splitlines():
        match = re.match(
            r"^\s*(?:[-*]\s+)?(?:\*\*)?([A-Za-z][A-Za-z0-9 _/-]{1,60}?)(?:\*\*)?:\s*(.*?)\s*$",
            line,
        )
        if match:
            key = _normalized_key(match.group(1))
            value = _clean_value(match.group(2))
            fields.setdefault(key, value)
            list_key = key if not value else ""
            if key in {"exact write paths", "write paths"} and value:
                paths.extend(
                    _clean_value(part)
                    for part in re.split(r"\s*[;,]\s*", value)
                    if _clean_value(part)
                )
            continue
        item = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if item and list_key in {"exact write paths", "write paths"}:
            value = _clean_value(item.group(1))
            if value:
                paths.append(value)
        elif line.strip() and not line.lstrip().startswith(("#", "```", "---")):
            list_key = ""
    if any(path.lower() in {"none", "n/a", "read-only"} for path in paths):
        paths = []
    return fields, list(dict.fromkeys(paths))[:32]


def _field(fields: dict[str, str], *names: str) -> str:
    for name in names:
        value = fields.get(_normalized_key(name), "")
        if value:
            return _clean_value(value)
    return ""


def _is_terminal(value: Any) -> bool:
    return bool(TERMINAL_STATUS.match(str(value or "").strip().upper()))


def _path_key(value: str | os.PathLike[str]) -> str:
    try:
        text = str(Path(value).resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        text = os.fspath(value)
    if os.name == "nt" and text.startswith("\\\\?\\"):
        text = text[4:]
    return os.path.normcase(os.path.normpath(text))


def _path_inside(path: str, root: Path) -> bool:
    candidate = _path_key(path)
    parent = _path_key(root)
    return candidate == parent or candidate.startswith(parent + os.sep)


def _paths_overlap(left: str, right: str, root: Path) -> bool:
    def resolved(value: str) -> str:
        candidate = Path(value)
        return _path_key(candidate if candidate.is_absolute() else root / candidate)

    one = resolved(left)
    two = resolved(right)
    return one == two or one.startswith(two + os.sep) or two.startswith(one + os.sep)


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_plugin_root(source: Path) -> Path:
    """Resolve one bounded, identity-checked Coordinator package shape."""
    try:
        resolved = Path(source).resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as error:
        raise RuntimeError(f"COORDINATOR_PACKAGE_IDENTITY_ERROR: invalid source path: {error}") from error
    start = resolved.parent if resolved.suffix else resolved
    candidates: list[Path] = []
    for current in (start, *list(start.parents)[:6]):
        candidates.extend((current, current / "plugins" / "codex-coordinator"))

    matches: dict[str, Path] = {}
    for candidate in candidates:
        manifest_path = candidate / ".codex-plugin" / "plugin.json"
        helper = (
            candidate
            / "skills"
            / "codex-coordinator"
            / "scripts"
            / "coordination_state.py"
        )
        scanner = candidate / "mission_control" / "doctor_scan.py"
        try:
            manifest = json.loads(_read_bounded(manifest_path, MAX_MARKER_BYTES))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            isinstance(manifest, dict)
            and manifest.get("name") == "codex-coordinator"
            and helper.is_file()
            and scanner.is_file()
        ):
            root = candidate.resolve(strict=False)
            matches[_path_key(root)] = root
    if len(matches) != 1:
        shape = "none" if not matches else "multiple"
        raise RuntimeError(
            "COORDINATOR_PACKAGE_IDENTITY_ERROR: "
            f"{shape} trusted Coordinator package shapes found within the bounded source path"
        )
    return next(iter(matches.values()))


def _database(codex_home: Path) -> Path | None:
    try:
        candidates = list(codex_home.glob("state_*.sqlite"))
        return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None
    except OSError:
        return None


def _rollout_metadata(path: Path) -> tuple[dict[str, Any], int]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - MAX_ROLLOUT_TAIL_BYTES)
            handle.seek(start)
            data = handle.read(MAX_ROLLOUT_TAIL_BYTES)
    except (OSError, ValueError):
        return {"state": "unknown", "completedAt": ""}, 0
    lines = data.splitlines()
    if start and lines:
        lines = lines[1:]
    state = "unknown"
    completed_at = ""
    event_count = 0
    for line in lines:
        prefix = line[:4096]
        row_type = re.search(rb'"type"\s*:\s*"(event_msg|response_item)"', prefix)
        payload = re.search(rb'"payload"\s*:\s*\{', prefix)
        if not row_type or not payload:
            continue
        segment = prefix[payload.end() :]
        payload_type = re.search(rb'"type"\s*:\s*"([A-Za-z0-9_]+)"', segment)
        if not payload_type:
            continue
        event_count += 1
        kind = payload_type.group(1).decode("ascii", errors="ignore")
        timestamp = re.search(rb'"timestamp"\s*:\s*"([^"\\]{1,80})"', prefix)
        stamp = timestamp.group(1).decode("ascii", errors="ignore") if timestamp else ""
        if row_type.group(1) == b"event_msg":
            if kind == "task_complete":
                state = "complete"
                completed_at = stamp
            elif kind == "user_message":
                state = "queued"
                completed_at = ""
            elif kind == "turn_aborted":
                state = "ended"
                completed_at = ""
            elif kind in {"agent_message", "agent_reasoning"}:
                state = "running"
                completed_at = ""
        else:
            role = re.search(rb'"role"\s*:\s*"([A-Za-z0-9_]+)"', segment[:1024])
            role_name = role.group(1).decode("ascii", errors="ignore") if role else ""
            if kind == "message" and role_name == "user":
                state = "queued"
                completed_at = ""
            elif kind in {"reasoning", "custom_tool_call", "function_call"} or (
                kind == "message" and role_name == "assistant"
            ):
                state = "running"
                completed_at = ""
    return {"state": state, "completedAt": completed_at, "events": event_count}, len(data)


def discover_project_roots(
    codex_home: Path,
    seeds: Iterable[Path] = (),
    *,
    include_native_inventory: bool = True,
) -> list[Path]:
    candidates = [Path(seed) for seed in seeds]
    database = _database(codex_home) if include_native_inventory else None
    if database:
        try:
            connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True, timeout=1)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
            if "cwd" in columns:
                candidates.extend(Path(row[0]) for row in connection.execute("SELECT DISTINCT cwd FROM threads") if row[0])
            connection.close()
        except (OSError, sqlite3.Error, ValueError):
            pass
    roots: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            continue
        for current in (resolved, *resolved.parents):
            marker = current / ".codex" / "coordination" / "project.yaml"
            values = _simple_yaml(_read_bounded(marker, MAX_MARKER_BYTES))
            if values.get("coordination_enabled", "").lower() != "true":
                continue
            key = _path_key(current)
            if key not in seen:
                roots.append(current)
                seen.add(key)
            break
    return roots


class DeterministicDoctorScanner:
    def __init__(self, source_root: Path, codex_home: Path):
        self.source_root = source_root.resolve(strict=False)
        self.plugin_root = resolve_plugin_root(source_root)
        self.codex_home = codex_home.resolve(strict=False)
        self.state = self._load_state_helper()
        self.reads = {
            "markers": 0,
            "currentStates": 0,
            "taskHeaders": 0,
            "inboxRecordsHashed": 0,
            "nativeRows": 0,
            "rolloutMetadataBytes": 0,
            "automationDefinitions": 0,
            "applicationFiles": 0,
            "transcriptBodies": 0,
            "modelCalls": 0,
            "modelTokens": 0,
        }

    def _load_state_helper(self) -> ModuleType:
        path = (
            self.plugin_root
            / "skills"
            / "codex-coordinator"
            / "scripts"
            / "coordination_state.py"
        )
        spec = importlib.util.spec_from_file_location("codex_coordinator_doctor_state", path)
        if not spec or not spec.loader:
            raise RuntimeError("Cannot load the packaged Coordinator state helper.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _finding(
        project_id: str,
        epoch: str,
        issue_code: str,
        severity: str,
        identities: Iterable[str],
        facts: Iterable[str],
        recommendation: str,
    ) -> dict[str, Any]:
        identity_list = sorted({str(value) for value in identities if str(value)})
        fact_list = sorted({re.sub(r"\s+", " ", str(value)).strip() for value in facts if str(value).strip()})
        fingerprint_input = {
            "projectId": project_id,
            "issueCode": issue_code,
            "identities": identity_list,
            "facts": fact_list,
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {
            "projectId": project_id,
            "coordinationEpoch": epoch,
            "issueCode": issue_code,
            "severity": severity,
            "identities": identity_list,
            "facts": fact_list,
            "recommendation": recommendation,
            "fingerprint": fingerprint,
            "findingId": f"DOCTOR-{fingerprint[:12].upper()}",
        }

    def _load_project(self, root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        coordination = root / ".codex" / "coordination"
        marker_data = _read_bounded(coordination / "project.yaml", MAX_MARKER_BYTES)
        self.reads["markers"] += 1
        marker = _simple_yaml(marker_data)
        if marker.get("coordination_enabled", "").lower() != "true":
            return None, []
        project_id = marker.get("project_id", "")
        findings: list[dict[str, Any]] = []
        if marker.get("schema_version") != "1" or not PROJECT_ID.fullmatch(project_id):
            findings.append(
                self._finding(
                    project_id or "unknown",
                    "UNKNOWN",
                    "MALFORMED_PROJECT_MARKER",
                    "HIGH",
                    [project_id or root.name],
                    ["project.yaml does not contain the supported schema and project identity"],
                    "Repair the marker before changing project coordination state.",
                )
            )
            return {"root": root, "coordination": coordination, "projectId": project_id or "unknown"}, findings
        current_path = coordination / "CURRENT.md"
        try:
            inspected = self.state.inspect_current(current_path)
            self.reads["currentStates"] += 1
        except (OSError, UnicodeError, self.state.StateError) as error:
            findings.append(
                self._finding(
                    project_id,
                    "UNKNOWN",
                    "MALFORMED_CURRENT_STATE",
                    "HIGH",
                    [project_id],
                    [str(error)],
                    "Have the project Coordinator repair CURRENT.md with the canonical state helper.",
                )
            )
            return {"root": root, "coordination": coordination, "projectId": project_id}, findings
        fields = inspected["fields"]
        epoch = fields["Coordination epoch"]
        if fields["Project ID"] != project_id:
            findings.append(
                self._finding(
                    project_id,
                    epoch,
                    "PROJECT_IDENTITY_MISMATCH",
                    "HIGH",
                    [project_id, fields["Project ID"]],
                    ["project.yaml and CURRENT.md project IDs differ"],
                    "Stop project routing until the canonical identity is reconciled.",
                )
            )
        tables = inspected["tables"]
        task_ids: set[str] = set()
        for heading in ("Active tasks", "Paused work", "Resume queue", "Blocked decisions"):
            task_ids.update(row.get("Task ID", "") for row in tables[heading] if row.get("Task ID"))
        for row in tables["Registered sessions"]:
            task_id = row.get("Task ID", "")
            if task_id and task_id.strip().lower() not in {"none", "-", "n/a"} and not _is_terminal(row.get("Status")):
                task_ids.add(task_id)
        contracts: dict[str, dict[str, Any]] = {}
        for task_id in sorted(task_ids):
            path = coordination / "tasks" / f"{task_id}.md"
            contract, paths = _task_contract(path)
            self.reads["taskHeaders"] += 1
            contracts[task_id] = {"exists": path.is_file(), "fields": contract, "paths": paths}
        return {
            "root": root,
            "coordination": coordination,
            "projectId": project_id,
            "epoch": epoch,
            "fields": fields,
            "tables": tables,
            "contracts": contracts,
        }, findings

    def _native_inventory(self, thread_ids: set[str]) -> tuple[dict[str, dict[str, Any]], bool]:
        database = _database(self.codex_home)
        if not database or not thread_ids:
            return {}, bool(database)
        result: dict[str, dict[str, Any]] = {}
        try:
            connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True, timeout=1)
            available = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
            required = {"id", "rollout_path", "archived", "updated_at", "cwd"}
            if not required.issubset(available):
                connection.close()
                return {}, False
            ids = sorted(thread_ids)
            for offset in range(0, len(ids), 250):
                chunk = ids[offset : offset + 250]
                placeholders = ",".join("?" for _ in chunk)
                query = (
                    "SELECT id, rollout_path, archived, updated_at, cwd FROM threads "
                    f"WHERE id IN ({placeholders})"
                )
                for thread_id, rollout_path, archived, updated_at, cwd in connection.execute(query, chunk):
                    metadata, bytes_read = _rollout_metadata(Path(str(rollout_path or "")))
                    self.reads["rolloutMetadataBytes"] += bytes_read
                    self.reads["nativeRows"] += 1
                    result[str(thread_id)] = {
                        **metadata,
                        "archived": bool(archived),
                        "updatedAt": updated_at,
                        "cwd": str(cwd or ""),
                    }
            connection.close()
        except (OSError, sqlite3.Error, ValueError):
            return {}, False
        return result, True

    def _native_titles(self, thread_ids: set[str]) -> dict[str, str]:
        """Read only native task titles; never open rollout/transcript files."""
        database = _database(self.codex_home)
        if not database or not thread_ids:
            return {}
        result: dict[str, str] = {}
        try:
            connection = sqlite3.connect(
                f"file:{database.as_posix()}?mode=ro", uri=True, timeout=1
            )
            available = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
            if not {"id", "title"}.issubset(available):
                connection.close()
                return {}
            ids = sorted(thread_ids)
            for offset in range(0, len(ids), 250):
                chunk = ids[offset : offset + 250]
                placeholders = ",".join("?" for _ in chunk)
                query = f"SELECT id, title FROM threads WHERE id IN ({placeholders})"
                for thread_id, title in connection.execute(query, chunk):
                    result[str(thread_id)] = _semantic_text(title, 160)
                    self.reads["nativeRows"] += 1
            connection.close()
        except (OSError, sqlite3.Error, ValueError):
            return {}
        return result

    def semantic_review_packet(self, roots: Iterable[Path]) -> dict[str, Any]:
        """Build the only data packet allowed into user-triggered model review."""
        projects: list[dict[str, Any]] = []
        seen: set[str] = set()
        for root in roots:
            resolved = Path(root).resolve(strict=False)
            key = _path_key(resolved)
            if key in seen:
                continue
            seen.add(key)
            project, _ = self._load_project(resolved)
            if project and project.get("fields"):
                projects.append(project)

        candidates: list[tuple[dict[str, Any], dict[str, str], str]] = []
        thread_ids: set[str] = set()
        for project in projects:
            active_task_ids = {
                row.get("Task ID", "") for row in project["tables"]["Active tasks"]
            }
            for session in project["tables"]["Registered sessions"]:
                task_id = session.get("Task ID", "")
                thread_id = session.get("Thread ID", "")
                if (
                    task_id not in active_task_ids
                    or session.get("Scope kind", "").upper() != "PROJECT_EXECUTION"
                    or session.get("Role", "").upper() not in WORKER_ROLES
                    or _is_terminal(session.get("Status"))
                    or not THREAD_ID.fullmatch(thread_id)
                ):
                    continue
                candidates.append((project, session, task_id))
                thread_ids.add(thread_id)

        titles = self._native_titles(thread_ids)
        tasks: list[dict[str, Any]] = []
        truncated = False
        for project, session, task_id in candidates:
            if len(tasks) >= MAX_SEMANTIC_REVIEW_TASKS:
                truncated = True
                break
            contract = project["contracts"].get(task_id, {})
            fields = contract.get("fields", {})
            identities = (
                project["projectId"],
                task_id,
                session.get("Thread ID", ""),
            )

            def bounded(value: Any, limit: int) -> str:
                text = str(value or "")
                for identity_value in identities:
                    if identity_value:
                        text = re.sub(
                            re.escape(str(identity_value)),
                            "[task]",
                            text,
                            flags=re.IGNORECASE,
                        )
                return _semantic_text(text, limit)

            title = bounded(titles.get(session.get("Thread ID", ""), ""), 160)
            goal = bounded(
                _field(fields, "individual goal", "goal", "objective"), 512
            )
            if not title and not goal:
                continue
            identity = "\0".join(
                (
                    project["projectId"],
                    str(project["epoch"]),
                    task_id,
                    session.get("Thread ID", ""),
                )
            )
            item = {
                "taskKey": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16],
                "threadTitle": title,
                "individualGoal": goal,
                "executionMode": bounded(
                    _field(fields, "execution mode"), 80
                ),
                "declaredWritePathCount": len(contract.get("paths", [])),
            }
            proposed = {
                "schemaVersion": 1,
                "checks": list(REVIEW_ONLY_CHECKS),
                "tasks": [*tasks, item],
                "truncated": truncated,
            }
            if len(json.dumps(proposed, ensure_ascii=False).encode("utf-8")) > MAX_SEMANTIC_PACKET_BYTES:
                truncated = True
                break
            tasks.append(item)

        return {
            "schemaVersion": 1,
            "checks": list(REVIEW_ONLY_CHECKS),
            "tasks": tasks,
            "truncated": truncated,
        }

    def _heartbeats(self) -> tuple[set[str], bool]:
        directory = self.codex_home / "automations"
        if not directory.is_dir():
            return set(), False
        targets: set[str] = set()
        try:
            paths = list(directory.glob("*/automation.toml"))
        except OSError:
            return set(), False
        for path in paths:
            data = _read_bounded(path, MAX_AUTOMATION_BYTES)
            if not data:
                continue
            self.reads["automationDefinitions"] += 1
            values: dict[bytes, bytes] = {}
            for line in data.splitlines():
                match = re.match(rb'^(kind|status|target_thread_id)\s*=\s*"([^"\\]*)"\s*$', line.strip())
                if match:
                    values[match.group(1)] = match.group(2)
            if values.get(b"kind", b"").lower() != b"heartbeat" or values.get(b"status", b"").upper() != b"ACTIVE":
                continue
            target = values.get(b"target_thread_id", b"").decode("ascii", errors="ignore")
            if THREAD_ID.fullmatch(target):
                targets.add(target)
        return targets, True

    def _inbox_cache_status(
        self, coordination: Path, project_id: str, epoch: int, coordinator_id: str
    ) -> str:
        scope = self.state._inbox_scope(project_id, epoch, coordinator_id)
        _, status = self.state._load_inbox_index(
            coordination / "cache" / "inbox-index.json", scope
        )
        return str(status)

    def _evaluate(
        self,
        project: dict[str, Any],
        native: dict[str, dict[str, Any]],
        native_available: bool,
        heartbeats: set[str],
        heartbeat_available: bool,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        project_id = project["projectId"]
        epoch = project["epoch"]
        fields = project["fields"]
        tables = project["tables"]
        contracts = project["contracts"]
        root = project["root"]
        findings: list[dict[str, Any]] = []
        limitations: list[str] = []

        def add(code: str, severity: str, identities: Iterable[str], facts: Iterable[str], recommendation: str) -> None:
            findings.append(self._finding(project_id, epoch, code, severity, identities, facts, recommendation))

        sessions = tables["Registered sessions"]
        active_rows = tables["Active tasks"]
        active_coordinators = [
            row
            for row in sessions
            if row.get("Role", "").upper() == "COORDINATOR"
            and row.get("Scope kind", "").upper() == "PROJECT_EXECUTION"
            and not _is_terminal(row.get("Status"))
        ]
        accepting_coordinators = [
            row for row in active_coordinators if row.get("Accepts project messages", "").lower() == "true"
        ]
        mode = fields["Coordination mode"].upper()
        shared_goal = fields["Shared goal"]
        requires_coordinator = True
        coordinator_id = fields["Coordinator thread ID"]
        if mode not in ACTIVE_COORDINATION_MODES:
            add(
                "INVALID_COORDINATION_MODE",
                "HIGH",
                [mode],
                ["enabled repositories require MANAGING, REPORT_ONLY, or ATTENTION_NEEDED"],
                "Migrate the canonical mode before claiming active management.",
            )
        if requires_coordinator and not accepting_coordinators:
            add(
                "ACTIVE_COORDINATOR_MISSING",
                "HIGH",
                [coordinator_id],
                [f"mode={mode}", "no non-terminal accepting project Coordinator is registered"],
                "Register exactly one accepting PROJECT_EXECUTION Coordinator before routing project work.",
            )
        if len(accepting_coordinators) > 1:
            add(
                "DUPLICATE_ACTIVE_COORDINATOR",
                "HIGH",
                [row.get("Thread ID", "") for row in accepting_coordinators],
                [f"accepting coordinators={len(accepting_coordinators)}"],
                "Reconcile to one exact accepting Coordinator identity.",
            )
        if accepting_coordinators and coordinator_id != accepting_coordinators[0].get("Thread ID"):
            add(
                "COORDINATOR_IDENTITY_MISMATCH",
                "HIGH",
                [coordinator_id, accepting_coordinators[0].get("Thread ID", "")],
                ["CURRENT.md Coordinator field and accepting session differ"],
                "Reconcile the canonical Coordinator fields and registered session.",
            )
        if requires_coordinator and fields["Accepts project messages"].lower() != "true":
            add(
                "COORDINATOR_NOT_ACCEPTING",
                "HIGH",
                [coordinator_id],
                ["canonical Coordinator acceptance is false while coordinated work remains"],
                "Restore an accepting Coordinator or explicitly close the coordinated goal.",
            )

        for row in sessions:
            if _is_terminal(row.get("Status")) and row.get("Accepts project messages", "").lower() == "true":
                add(
                    "TERMINAL_SESSION_ACCEPTING",
                    "HIGH",
                    [row.get("Thread ID", ""), row.get("Task ID", "")],
                    [f"status={row.get('Status', '')}", "accepts_project_messages=true"],
                    "Close message acceptance for the terminal session.",
                )

        session_by_task = {
            row.get("Task ID", ""): row
            for row in sessions
            if row.get("Task ID", "").strip().lower() not in {"", "none", "-", "n/a"}
        }
        for row in active_rows:
            task_id = row.get("Task ID", "")
            record = contracts.get(task_id, {})
            if not record.get("exists"):
                add(
                    "TASK_CONTRACT_MISSING",
                    "HIGH",
                    [task_id],
                    ["active task has no task record"],
                    "Create or recover the canonical task contract before work continues.",
                )
                continue
            contract = record["fields"]
            mismatches: list[str] = []
            if _field(contract, "project id") and _field(contract, "project id") != project_id:
                mismatches.append("project_id")
            if _field(contract, "coordination epoch", "epoch") and _field(contract, "coordination epoch", "epoch") != epoch:
                mismatches.append("coordination_epoch")
            if _field(contract, "task id") and _field(contract, "task id") != task_id:
                mismatches.append("task_id")
            owner = _field(contract, "owner thread", "recipient")
            if owner and row.get("Owner") and owner != row.get("Owner"):
                mismatches.append("owner_thread")
            session = session_by_task.get(task_id)
            if not session:
                mismatches.append("registered_session")
            elif _is_terminal(session.get("Status")):
                mismatches.append("terminal_session")
            if mismatches:
                add(
                    "TASK_OWNERSHIP_MISMATCH",
                    "HIGH",
                    [task_id, row.get("Owner", ""), owner],
                    [f"mismatched={','.join(sorted(mismatches))}"],
                    "Pause the task and reconcile its contract, owner, and registered session.",
                )
            thread_id = session.get("Thread ID", "") if session else ""
            receipt = native.get(thread_id)
            completed = _parse_time(receipt.get("completedAt")) if receipt else None
            reconciled = _parse_time(fields["Last reconciliation"])
            if receipt and receipt.get("state") == "complete" and completed and reconciled and reconciled > completed:
                add(
                    "COMPLETED_WORKER_STILL_ACTIVE",
                    "MEDIUM",
                    [task_id, thread_id],
                    ["native worker turn completed before the later canonical reconciliation"],
                    "Reconcile the terminal worker receipt and release or requeue ownership explicitly.",
                )

        scoped = [
            (row.get("Task ID", ""), contracts.get(row.get("Task ID", ""), {}).get("paths", []))
            for row in active_rows
        ]
        for index, (left_id, left_paths) in enumerate(scoped):
            for right_id, right_paths in scoped[index + 1 :]:
                overlap = next(
                    (
                        left
                        for left in left_paths
                        for right in right_paths
                        if _paths_overlap(left, right, root)
                    ),
                    "",
                )
                if overlap:
                    add(
                        "EXCLUSIVE_OWNERSHIP_OVERLAP",
                        "HIGH",
                        [left_id, right_id],
                        [f"overlapping declared path={overlap}"],
                        "Pause one owner and record one exclusive write boundary.",
                    )

        for row in tables["Pending commands"]:
            if row.get("Status", "").upper().startswith(("ACK", "COMPLETE", "DONE")):
                add(
                    "ACKNOWLEDGED_COMMAND_STILL_PENDING",
                    "MEDIUM",
                    [row.get("Task ID", ""), row.get("Message ID", "")],
                    [f"pending command status={row.get('Status', '')}"],
                    "Remove or transition the acknowledged command at the next reconciliation.",
                )

        workers = [
            row
            for row in sessions
            if row.get("Scope kind", "").upper() == "PROJECT_EXECUTION"
            and row.get("Role", "").upper() in WORKER_ROLES
            and not _is_terminal(row.get("Status"))
        ]
        if len(workers) > 5:
            add(
                "WORKER_CEILING_EXCEEDED",
                "HIGH",
                [row.get("Thread ID", "") for row in workers],
                [f"non-terminal project workers={len(workers)}"],
                "Stop new worker creation and reconcile to the recorded ceiling or user override.",
            )
        elif len(workers) >= 4:
            missing_reason = []
            for row in workers:
                task_id = row.get("Task ID", "")
                contract = contracts.get(task_id, {}).get("fields", {})
                if not _field(contract, "durable lane reason", "parallel lane reason", "critical path reason"):
                    missing_reason.append(task_id)
            if missing_reason:
                add(
                    "WORKER_LANE_REASON_MISSING",
                    "MEDIUM",
                    missing_reason,
                    [f"workers without a structured durable-lane reason={len(missing_reason)}"],
                    "Record why every fourth or fifth durable lane shortens the critical path.",
                )

        coordinator_native = native.get(coordinator_id)
        if native_available and coordinator_id not in {"NONE", "UNAVAILABLE"}:
            if not coordinator_native:
                add(
                    "COORDINATOR_NATIVE_IDENTITY_MISSING",
                    "HIGH",
                    [coordinator_id],
                    ["canonical Coordinator thread is absent from native task metadata"],
                    "Recover or replace the Coordinator through the documented recovery path.",
                )
            else:
                if coordinator_native.get("archived"):
                    add(
                        "COORDINATOR_NATIVE_TERMINAL",
                        "HIGH",
                        [coordinator_id],
                        ["canonical accepting Coordinator is archived natively"],
                        "Recover or replace the Coordinator before sending project messages.",
                    )
                if coordinator_native.get("cwd") and not _path_inside(coordinator_native["cwd"], root):
                    add(
                        "FOREIGN_COORDINATOR_IDENTITY",
                        "HIGH",
                        [coordinator_id],
                        ["native Coordinator working directory is outside the enabled project root"],
                        "Stop routing and register the exact same-project Coordinator.",
                    )
        elif not native_available and THREAD_ID.fullmatch(coordinator_id):
            limitations.append("native-status-unavailable")

        if (
            coordinator_native
            and heartbeat_available
            and coordinator_id not in heartbeats
        ):
            add(
                "UNATTENDED_RETURN_PATH",
                "HIGH",
                [coordinator_id],
                ["enabled repository has no active heartbeat targeting its Coordinator"],
                "Create the one repository heartbeat and keep it while Coordinator remains enabled.",
            )
        elif not heartbeat_available:
            limitations.append("heartbeat-inventory-unavailable")

        if coordinator_id not in {"NONE", "UNAVAILABLE"}:
            try:
                cache_status = self._inbox_cache_status(
                    project["coordination"], project_id, int(epoch), coordinator_id
                )
                if cache_status == "current":
                    inbox = self.state.scan_inbox(
                        project["coordination"],
                        project_id=project_id,
                        coordination_epoch=int(epoch),
                        coordinator_id=coordinator_id,
                    )
                    self.reads["inboxRecordsHashed"] += len(inbox.get("pendingRecords", [])) + int(
                        inbox.get("acknowledgedCount", 0)
                    )
                else:
                    inbox = {"pendingRecords": []}
                if cache_status == "current" and coordinator_native:
                    completed_at = _parse_time(coordinator_native.get("completedAt"))
                    for record in inbox.get("pendingRecords", []):
                        path = project["coordination"] / record["path"]
                        try:
                            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                        except OSError:
                            continue
                        if completed_at and completed_at > modified:
                            add(
                                "UNPROCESSED_INBOX_AFTER_COORDINATOR_TURN",
                                "MEDIUM",
                                [record["path"], coordinator_id],
                                ["inbox record remains unacknowledged after a later completed Coordinator turn"],
                                "Validate and disposition the inbox record at the next reconciliation.",
                            )
                elif cache_status != "current" and any(
                    (project["coordination"] / "inbox").glob("*.md")
                ):
                    limitations.append("inbox-checkpoint-not-current")
            except (OSError, UnicodeError, ValueError, self.state.StateError):
                limitations.append("inbox-scan-unavailable")

        return findings, sorted(set(limitations))

    def _existing_fingerprints(self, coordination: Path) -> set[str]:
        fingerprints: set[str] = set()
        try:
            paths = list((coordination / "inbox").glob("*.md"))
        except OSError:
            return fingerprints
        for path in paths:
            data = _read_bounded(path, MAX_INBOX_HEADER_BYTES)
            if not re.search(rb"(?m)^type:\s*DOCTOR_FINDING\s*$", data):
                continue
            match = re.search(rb"(?m)^fingerprint:\s*([0-9a-f]{64})\s*$", data)
            if match:
                fingerprints.add(match.group(1).decode("ascii"))
        return fingerprints

    def _write_findings(self, projects: list[dict[str, Any]], findings: list[dict[str, Any]]) -> int:
        project_by_id = {project["projectId"]: project for project in projects}
        existing = {
            project_id: self._existing_fingerprints(project["coordination"])
            for project_id, project in project_by_id.items()
        }
        written = 0
        for finding in findings:
            project = project_by_id.get(finding["projectId"])
            if not project or finding["fingerprint"] in existing[finding["projectId"]]:
                continue
            detected = datetime.now(timezone.utc)
            filename = f"{detected.strftime('%Y%m%dT%H%M%S%fZ')}-doctor-{finding['fingerprint'][:12]}.md"
            facts = "\n".join(f"- {fact}" for fact in finding["facts"])
            identities = ", ".join(finding["identities"]) or "none"
            content = f"""type: DOCTOR_FINDING
project_id: {finding['projectId']}
coordination_epoch: {finding['coordinationEpoch']}
finding_id: {finding['findingId']}
fingerprint: {finding['fingerprint']}
reported_by: CODEX_COORDINATOR_DOCTOR
state: REVIEW_NEEDED
severity: {finding['severity']}
detected_at: {detected.isoformat().replace('+00:00', 'Z')}

# {finding['issueCode']}

Affected identities: {identities}

Minimal evidence:
{facts}

Recommended Coordinator disposition: {finding['recommendation']}

Safe work may continue only outside the affected ownership or routing boundary. A real user decision is required only if the Coordinator cannot repair or disposition this mismatch within its existing authority.
"""
            try:
                self.state.create_file(
                    project["coordination"],
                    Path("inbox") / filename,
                    content.encode("utf-8"),
                )
            except (OSError, self.state.StateError):
                continue
            existing[finding["projectId"]].add(finding["fingerprint"])
            finding["reportPath"] = f"inbox/{filename}"
            written += 1
        return written

    def scan(self, roots: Iterable[Path], *, write_findings: bool = False) -> dict[str, Any]:
        projects: list[dict[str, Any]] = []
        project_contexts: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        seen: set[str] = set()
        projects_checked = 0
        for root in roots:
            resolved = Path(root).resolve(strict=False)
            key = _path_key(resolved)
            if key in seen:
                continue
            seen.add(key)
            project, project_findings = self._load_project(resolved)
            findings.extend(project_findings)
            if project:
                projects_checked += 1
                project_contexts.append(project)
                if project.get("fields"):
                    projects.append(project)
        thread_ids: set[str] = set()
        for project in projects:
            coordinator_id = project["fields"]["Coordinator thread ID"]
            if THREAD_ID.fullmatch(coordinator_id):
                thread_ids.add(coordinator_id)
            active_task_ids = {
                row.get("Task ID", "") for row in project["tables"]["Active tasks"]
            }
            thread_ids.update(
                row.get("Thread ID", "")
                for row in project["tables"]["Registered sessions"]
                if row.get("Task ID", "") in active_task_ids
                and THREAD_ID.fullmatch(row.get("Thread ID", ""))
            )
        native, native_available = self._native_inventory(thread_ids)
        heartbeats, heartbeat_available = self._heartbeats()
        limitations: dict[str, list[str]] = {}
        for project in projects:
            project_findings, project_limitations = self._evaluate(
                project, native, native_available, heartbeats, heartbeat_available
            )
            findings.extend(project_findings)
            if project_limitations:
                limitations[project["projectId"]] = project_limitations
        unique: dict[str, dict[str, Any]] = {finding["fingerprint"]: finding for finding in findings}
        findings = sorted(
            unique.values(),
            key=lambda item: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(item["severity"], 3), item["projectId"], item["issueCode"]),
        )
        written = self._write_findings(project_contexts, findings) if write_findings else 0
        status = "review" if findings or limitations else "healthy"
        return {
            "schemaVersion": 1,
            "status": status,
            "projectsChecked": projects_checked,
            "findingCount": len(findings),
            "findingsWritten": written,
            "issueCodes": sorted({finding["issueCode"] for finding in findings}),
            "projectsNeedingReview": sorted({finding["projectId"] for finding in findings}),
            "findings": findings,
            "coverage": {
                "deterministic": True,
                "reviewOnly": list(REVIEW_ONLY_CHECKS),
                "limitations": limitations,
            },
            "reads": dict(self.reads),
        }


def compact_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report["status"],
        "projectsChecked": report["projectsChecked"],
        "findingCount": report["findingCount"],
        "findingsWritten": report["findingsWritten"],
        "issueCodes": report["issueCodes"],
        "projectsNeedingReview": report["projectsNeedingReview"],
        "reviewOnlyChecks": report["coverage"]["reviewOnly"],
        "limitations": report["coverage"]["limitations"],
        "reads": report["reads"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the zero-model Coordinator project Doctor.")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve())
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    parser.add_argument("--project-root", type=Path, action="append", default=[])
    parser.add_argument("--write-findings", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    seeds = list(args.project_root) if args.project_root else [args.source_root]
    roots = discover_project_roots(
        args.codex_home,
        seeds,
        include_native_inventory=not bool(args.project_root),
    )
    try:
        report = DeterministicDoctorScanner(args.source_root, args.codex_home).scan(
            roots, write_findings=args.write_findings
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, separators=(",", ":")))
        return 1
    output = compact_report(report) if args.compact else report
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":") if args.compact else None, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
