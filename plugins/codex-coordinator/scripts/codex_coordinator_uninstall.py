#!/usr/bin/env python3
"""Dry-run-first lifecycle changes for Coordinator project markers.

Schema 2 has no Coordinator task, heartbeat, schedule, or Mission Control
lifecycle. Legacy schema-1 cleanup actions are reported only when old project
state proves that those components may still exist.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DISCOVERY_BLOCK = """## Codex Coordinator

- This repository uses the opt-in Codex task-boundary board in `.codex/coordination/project.yaml`.
- Before substantial writes, load the installed `codex-coordinator` skill, list active claims from the primary worktree, and publish only this task's bounded claim.
- Native Codex tasks remain the execution, messaging, and transcript authority; there is no resident Coordinator, heartbeat, or mandatory pull-request workflow.
- Reject cross-project notices and never store transcripts, reasoning, prompts, or tool output in Coordinator state."""

LEGACY_DISCOVERY_BLOCKS = (
    """## Codex Coordinator

- This repository is Codex Coordinator-enabled.
- Project identity is in `.codex/coordination/project.yaml`; current coordination state is in `.codex/coordination/CURRENT.md`.
- Load the globally installed `codex-coordinator` skill at the start of every task in this repository; all same-repository tasks are managed by default unless the user explicitly excludes one.
- Respect the project ID and assigned task boundary; reject missing or mismatched cross-thread project bindings.
- Treat Coordinator internals as protected; only an explicitly user-authorised `COORDINATOR_MAINTAINER` may modify them.""",
    """## Codex Coordinator

- This repository is Codex Coordinator-enabled.
- Project identity is in `.codex/coordination/project.yaml`; current coordination state is in `.codex/coordination/CURRENT.md`.
- Load the globally installed `codex-coordinator` skill before substantial, overlapping, parallel, or cross-thread work.
- Respect the project ID and assigned task boundary; reject missing or mismatched cross-thread project bindings.
- Treat Coordinator internals as protected; only an explicitly user-authorised `COORDINATOR_MAINTAINER` may modify them.""",
)

IGNORE_BLOCK = ".codex/coordination/*\n!.codex/coordination/project.yaml"
INDEX_SCHEMA = 1
QUARANTINE_NAME = "coordination.codex-coordinator-purge"
MARKER_KEYS = ("schema_version", "coordination_enabled", "project_id")


class LifecycleError(RuntimeError):
    """Raised when a lifecycle precondition is unsafe or ambiguous."""


@dataclass(frozen=True)
class Document:
    path: Path
    raw: bytes
    text: str
    newline: str
    bom: bool

    def encode(self, text: str) -> bytes:
        payload = text.encode("utf-8")
        return (b"\xef\xbb\xbf" + payload) if self.bom else payload


@dataclass(frozen=True)
class Project:
    root: Path
    coordination: Path
    marker: Document
    fields: dict[str, str]
    resumed_purge: bool

    @property
    def project_id(self) -> str:
        return self.fields["project_id"]

    @property
    def enabled(self) -> bool:
        return self.fields["coordination_enabled"] == "true"

    @property
    def schema(self) -> int:
        return int(self.fields["schema_version"])


def _read_document(path: Path, *, required: bool = True) -> Document | None:
    if not path.exists():
        if required:
            raise LifecycleError(f"required file is missing: {path}")
        return None
    if not path.is_file():
        raise LifecycleError(f"expected a file: {path}")
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise LifecycleError(f"file is not UTF-8: {path}") from error
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return Document(path=path, raw=raw, text=text, newline=newline, bom=bom)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _is_linklike(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.exists() and path.is_junction()
    )


def _require_contained_directory(root: Path, path: Path, *, label: str) -> None:
    if _is_linklike(path):
        raise LifecycleError(f"{label} must not be a symlink or junction: {path}")
    if path.exists() and not path.is_dir():
        raise LifecycleError(f"{label} must be a directory: {path}")
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError as error:
        raise LifecycleError(f"{label} escapes the project root: {path}") from error


def _git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        raise LifecycleError(f"Git validation failed for {root}")
    return result.stdout


def _validate_primary_worktree(root: Path) -> None:
    top = Path(_git_output(root, "rev-parse", "--show-toplevel").strip())
    if not _same_path(root, top):
        raise LifecycleError("project root must equal the Git worktree root")
    listing = _git_output(root, "worktree", "list", "--porcelain").splitlines()
    first = next((line[9:] for line in listing if line.startswith("worktree ")), None)
    if not first or not _same_path(root, Path(first)):
        raise LifecycleError("lifecycle changes must run from the primary Git worktree")


def _parse_marker(document: Document) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in MARKER_KEYS:
        matches = re.findall(rf"(?m)^{re.escape(key)}:\s*([^\r\n#]+?)\s*$", document.text)
        if len(matches) != 1:
            raise LifecycleError(f"marker must contain exactly one {key}")
        fields[key] = matches[0].strip()
    if fields["schema_version"] not in {"1", "2"}:
        raise LifecycleError("only marker schema 1 and 2 are supported")
    if fields["coordination_enabled"] not in {"true", "false"}:
        raise LifecycleError("coordination_enabled must be true or false")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", fields["project_id"]):
        raise LifecycleError("project_id is invalid")
    return fields


def _load_project(root_value: str, *, allow_resumed_purge: bool = False) -> Project:
    root = Path(root_value).expanduser().resolve()
    if not root.is_dir():
        raise LifecycleError(f"project root is not a directory: {root}")
    _validate_primary_worktree(root)
    codex_directory = root / ".codex"
    coordination = codex_directory / "coordination"
    quarantine = codex_directory / QUARANTINE_NAME
    _require_contained_directory(root, codex_directory, label=".codex directory")
    _require_contained_directory(root, coordination, label="coordination directory")
    _require_contained_directory(root, quarantine, label="purge quarantine")
    resumed = False
    if not coordination.exists() and allow_resumed_purge and quarantine.is_dir():
        coordination = quarantine
        resumed = True
    elif quarantine.exists():
        raise LifecycleError(f"purge quarantine already exists: {quarantine}")
    marker = _read_document(coordination / "project.yaml")
    assert marker is not None
    return Project(root, coordination, marker, _parse_marker(marker), resumed)


def _replace_marker_enabled(document: Document, enabled: bool) -> str:
    replacement = "true" if enabled else "false"
    updated, count = re.subn(
        r"(?m)^coordination_enabled:\s*(?:true|false)\s*$",
        f"coordination_enabled: {replacement}",
        document.text,
    )
    if count != 1:
        raise LifecycleError("marker enablement field is ambiguous")
    return updated


def _validate_schema_two_reactivation(document: Document) -> None:
    expected = {
        "active": ".codex/coordination/active",
        "archive": ".codex/coordination/archive",
        "cross_project_task_access": "false",
        "cross_project_state_changes": "false",
    }
    for key, value in expected.items():
        matches = re.findall(
            rf"(?m)^\s*{re.escape(key)}:\s*([^\r\n#]+?)\s*$", document.text
        )
        if len(matches) != 1 or matches[0].strip() != value:
            raise LifecycleError(f"schema-2 marker has incompatible {key}")


def _block_for(document: Document, block: str) -> str:
    return block.replace("\n", document.newline)


def _remove_exact_block(document: Document, block: str, label: str) -> str:
    rendered = _block_for(document, block)
    count = document.text.count(rendered)
    if count > 1:
        raise LifecycleError(f"duplicate {label} blocks found")
    if count == 0:
        if label == "Coordinator discovery" and "## Codex Coordinator" in document.text:
            raise LifecycleError("Coordinator discovery block differs from the packaged contract")
        return document.text
    start = document.text.index(rendered)
    end = start + len(rendered)
    if start >= len(document.newline) and document.text[:start].endswith(document.newline * 2):
        start -= len(document.newline)
    if document.text[end:].startswith(document.newline):
        end += len(document.newline)
    return document.text[:start] + document.text[end:]


def _remove_discovery_block(document: Document) -> str:
    matches: list[str] = []
    for block in (DISCOVERY_BLOCK, *LEGACY_DISCOVERY_BLOCKS):
        count = document.text.count(_block_for(document, block))
        if count > 1:
            raise LifecycleError("duplicate Coordinator discovery blocks found")
        if count == 1:
            matches.append(block)
    if len(matches) > 1:
        raise LifecycleError("multiple supported Coordinator discovery blocks found")
    if not matches:
        if "## Codex Coordinator" in document.text:
            raise LifecycleError("Coordinator discovery block differs from the packaged contract")
        return document.text
    return _remove_exact_block(document, matches[0], "supported Coordinator discovery")


def _ensure_current_discovery(document: Document | None, path: Path) -> tuple[Document, str]:
    if document is None:
        return _add_exact_block(None, path, DISCOVERY_BLOCK, "Coordinator discovery")
    if document.text.count(_block_for(document, DISCOVERY_BLOCK)) == 1:
        return document, document.text
    normalized = _remove_discovery_block(document)
    source = Document(document.path, document.raw, normalized, document.newline, document.bom)
    return _add_exact_block(source, path, DISCOVERY_BLOCK, "Coordinator discovery")


def _add_exact_block(document: Document | None, path: Path, block: str, label: str) -> tuple[Document, str]:
    if document is None:
        empty = Document(path, b"", "", "\n", False)
        return empty, block + "\n"
    rendered = _block_for(document, block)
    count = document.text.count(rendered)
    if count > 1:
        raise LifecycleError(f"duplicate {label} blocks found")
    if count == 1:
        return document, document.text
    if label == "Coordinator discovery" and "## Codex Coordinator" in document.text:
        raise LifecycleError("Coordinator discovery block differs from the packaged contract")
    separator = "" if not document.text else (document.newline if document.text.endswith(document.newline) else document.newline * 2)
    if document.text.endswith(document.newline) and not document.text.endswith(document.newline * 2):
        separator = document.newline
    return document, document.text + separator + rendered + document.newline


def _coordinator_id(project: Project) -> str | None:
    current = _read_document(project.coordination / "CURRENT.md", required=False)
    if current is None:
        return None
    matches = re.findall(r"(?m)^\*\*Coordinator thread ID:\*\*\s*(\S+)\s*$", current.text)
    return matches[0] if len(matches) == 1 and matches[0] != "NONE" else None


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(prefix=path.name + ".", suffix=".tmp", dir=path.parent, delete=False)
    temp = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _apply_documents(changes: Iterable[tuple[Document, str]]) -> None:
    prepared = [(document, document.encode(text)) for document, text in changes if document.raw != document.encode(text)]
    written: list[Document] = []
    try:
        for document, payload in prepared:
            _atomic_write(document.path, payload)
            written.append(document)
    except Exception:
        for document in reversed(written):
            _atomic_write(document.path, document.raw)
        raise


def _native_actions(project: Project, *, activate: bool) -> list[dict[str, str]]:
    if project.schema == 2:
        return []
    coordinator = _coordinator_id(project)
    if activate:
        raise LifecycleError(
            "legacy schema 1 cannot be reactivated; migrate the disabled marker to schema 2"
        )
    actions = [{"action": "remove-repository-heartbeat", "targetThreadId": coordinator or "verify-current-coordinator"}]
    if coordinator:
        actions.extend(
            [
                {"action": "archive-coordinator-at-safe-boundary", "targetThreadId": coordinator},
                {"action": "unpin-coordinator", "targetThreadId": coordinator},
            ]
        )
    return actions


def project_operation(args: argparse.Namespace) -> dict[str, object]:
    purge = args.action == "purge"
    project = _load_project(args.project_root, allow_resumed_purge=purge)
    agents_path = project.root / "AGENTS.md"
    ignore_path = project.root / ".gitignore"
    agents = _read_document(agents_path, required=False)
    ignore = _read_document(ignore_path, required=False)
    actions: list[dict[str, str]] = []
    changes: list[tuple[Document, str]] = []

    if args.action == "deactivate":
        if project.resumed_purge:
            raise LifecycleError("cannot deactivate a project while purge is incomplete")
        marker_text = _replace_marker_enabled(project.marker, False)
        if marker_text != project.marker.text:
            actions.append({"action": "set-marker-disabled", "path": str(project.marker.path)})
            changes.append((project.marker, marker_text))
        if agents is not None:
            agents_text = _remove_discovery_block(agents)
            if agents_text != agents.text:
                actions.append({"action": "remove-discovery-block", "path": str(agents.path)})
                changes.append((agents, agents_text))
        native = _native_actions(project, activate=False)

    elif args.action == "reactivate":
        if project.resumed_purge:
            raise LifecycleError("cannot reactivate a project while purge is incomplete")
        if project.schema != 2:
            raise LifecycleError(
                "legacy schema 1 cannot be reactivated; migrate the disabled marker to schema 2"
            )
        _validate_schema_two_reactivation(project.marker)
        marker_text = _replace_marker_enabled(project.marker, True)
        if marker_text != project.marker.text:
            actions.append({"action": "set-marker-enabled", "path": str(project.marker.path)})
            changes.append((project.marker, marker_text))
        agents_document, agents_text = _ensure_current_discovery(agents, agents_path)
        if agents_text != agents_document.text:
            actions.append({"action": "restore-discovery-block", "path": str(agents_path)})
            changes.append((agents_document, agents_text))
        native = _native_actions(project, activate=True)

    else:
        if args.confirm_project_id != project.project_id:
            raise LifecycleError("purge requires --confirm-project-id matching the validated marker")
        if agents is not None:
            agents_text = _remove_discovery_block(agents)
            if agents_text != agents.text:
                actions.append({"action": "remove-discovery-block", "path": str(agents.path)})
                changes.append((agents, agents_text))
        if ignore is not None:
            ignore_text = _remove_exact_block(ignore, IGNORE_BLOCK, "Coordinator ignore")
            if ignore_text != ignore.text:
                actions.append({"action": "remove-ignore-block", "path": str(ignore.path)})
                changes.append((ignore, ignore_text))
        actions.append({"action": "remove-coordination-state", "path": str(project.coordination)})
        native = _native_actions(project, activate=False)

    if args.apply:
        _apply_documents(changes)
        if purge:
            quarantine = project.root / ".codex" / QUARANTINE_NAME
            if not project.resumed_purge:
                os.replace(project.coordination, quarantine)
            shutil.rmtree(quarantine)

    return {
        "status": "applied" if args.apply else "planned",
        "operation": args.action,
        "projectId": project.project_id,
        "projectRoot": str(project.root),
        "actions": actions,
        "requiredNativeActions": native,
        "historyPreserved": not purge,
    }


def _load_index(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LifecycleError(f"project index is invalid: {path}") from error
    if payload.get("schemaVersion") != INDEX_SCHEMA or not isinstance(payload.get("projects"), list):
        raise LifecycleError(f"project index schema is invalid: {path}")
    projects: list[dict[str, str]] = []
    for entry in payload["projects"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("projectId"), str) or not isinstance(entry.get("path"), str):
            raise LifecycleError(f"project index entry is invalid: {path}")
        projects.append({"projectId": entry["projectId"], "path": entry["path"]})
    return projects


def index_project(args: argparse.Namespace) -> dict[str, object]:
    project = _load_project(args.project_root)
    codex_home = Path(args.codex_home).expanduser().resolve()
    index_path = codex_home / "codex-coordinator" / "projects.json"
    entries = _load_index(index_path)
    keyed = {os.path.normcase(str(Path(entry["path"]).expanduser().resolve())): entry for entry in entries}
    keyed[os.path.normcase(str(project.root))] = {"projectId": project.project_id, "path": str(project.root)}
    payload = {
        "schemaVersion": INDEX_SCHEMA,
        "projects": sorted(keyed.values(), key=lambda item: (item["projectId"], item["path"])),
    }
    encoded = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    if args.apply:
        _atomic_write(index_path, encoded)
    return {
        "status": "applied" if args.apply else "planned",
        "operation": "index-project",
        "indexPath": str(index_path),
        "project": {"projectId": project.project_id, "path": str(project.root)},
    }


def global_plan(args: argparse.Namespace) -> dict[str, object]:
    codex_home = Path(args.codex_home).expanduser().resolve()
    index_path = codex_home / "codex-coordinator" / "projects.json"
    candidates = _load_index(index_path)
    candidates.extend({"projectId": "unverified", "path": value} for value in args.project_root)
    unique: dict[str, dict[str, str]] = {}
    for entry in candidates:
        path = str(Path(entry["path"]).expanduser().resolve())
        unique[os.path.normcase(path)] = {"projectId": entry["projectId"], "path": path}

    verified: list[dict[str, object]] = []
    rejected: list[dict[str, str]] = []
    for entry in unique.values():
        try:
            project = _load_project(entry["path"])
            if entry["projectId"] not in {"unverified", project.project_id}:
                raise LifecycleError("index project ID does not match marker")
            verified.append(
                {
                    "projectId": project.project_id,
                    "path": str(project.root),
                    "enabled": project.enabled,
                    "requiredNativeActions": _native_actions(project, activate=False),
                }
            )
        except LifecycleError as error:
            rejected.append({"path": entry["path"], "reason": str(error)})

    return {
        "status": "planned",
        "operation": "global-uninstall",
        "indexPath": str(index_path),
        "verifiedProjects": verified,
        "rejectedProjects": rejected,
        "requiredGlobalActions": [
            "deactivate each verified enabled project",
            "for legacy schema-1 projects only, stop verified old heartbeats and Coordinator tasks",
            "stop any separately configured legacy Mission Control automatic startup",
            "codex plugin remove codex-coordinator@codex-coordinator",
            "optionally remove the codex-coordinator marketplace when directly requested",
        ],
        "projectHistoryPreserved": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    project = subparsers.add_parser("project", help="plan or apply one project lifecycle operation")
    project.add_argument("action", choices=("deactivate", "reactivate", "purge"))
    project.add_argument("--project-root", required=True)
    project.add_argument("--apply", action="store_true", help="apply the planned filesystem changes")
    project.add_argument("--confirm-project-id", help="required for destructive project purge")
    project.set_defaults(handler=project_operation)

    index = subparsers.add_parser("index-project", help="record one verified project in the bounded local index")
    index.add_argument("--project-root", required=True)
    index.add_argument("--codex-home", required=True)
    index.add_argument("--apply", action="store_true")
    index.set_defaults(handler=index_project)

    global_uninstall = subparsers.add_parser("global-plan", help="plan global uninstall from verified known projects")
    global_uninstall.add_argument("--codex-home", required=True)
    global_uninstall.add_argument("--project-root", action="append", default=[])
    global_uninstall.set_defaults(handler=global_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except (LifecycleError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
