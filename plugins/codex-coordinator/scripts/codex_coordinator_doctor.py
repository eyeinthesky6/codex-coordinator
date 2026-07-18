from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PLUGIN_NAME = "codex-coordinator"
HOOK_NAME = "codex_coordinator_session_start.py"
CAPABILITY_CONTRACT = "capabilities.json"
CAPABILITY_CONTRACT_VERSION = 14
REQUIRED_CAPABILITIES: dict[str, Any] = {
    "workerCreation": "full-assignment-first-turn",
    "coordinatorRole": "control-first",
    "doctorDiagnostics": "json-with-optional-mermaid",
    "doctorProjectScan": "deterministic-structured-state-zero-model",
    "doctorSemanticReview": "user-triggered-allowlisted-low-candidate-only",
    "monitoring": "heartbeat-with-single-wake-fallback",
    "modelDefault": "inherit-unless-user-overrides",
    "reasoningDefault": "low-or-medium",
    "registrationDelivery": "document-only-no-ack",
    "workerGranularity": "durable-complex-only",
    "microtaskExecution": "current-owner-or-parent-subagent",
    "parallelWorkerTarget": "one-to-three-default-five-max",
    "stateTool": "scripts/coordination_state.py",
    "subagents": "allowed-parent-owned",
    "operationsGuidance": "split-by-action-lane",
    "coordinationReadCache": "two-phase-inbox-hash-checkpoint",
    "nativeTaskReads": "host-cursor-no-mirror",
    "continuationGuarantee": "verified-return-path-before-final",
    "archivedRecovery": "direct-request-no-repeat-confirmation",
    "externalWriteDisclosure": "prewrite-notice-and-scope-authority",
    "subagentDispatch": "one-to-three-for-two-independent-lanes",
}
REQUIRED_TASK_LIFECYCLE = {
    "pin-coordinator",
    "rename-worker",
    "archive-terminal-worker",
    "fork-same-goal-only",
    "handoff-explicit",
}
REQUIRED_GUIDANCE = {
    "SKILL.md": (
        "Coordinator is control-first by default",
        "one temporary native heartbeat",
        "end-of-turn continuation gate",
        "set reasoning explicitly to `low`",
        "Subagents remain available as parent-owned helpers",
        "Use one to three parent-owned subagents when two or more independent, bounded",
        "Do not spawn them for a single trivial command",
        "durable-thread gate",
        "Task registration, acceptance, ownership recording",
        "scripts/coordination_state.py",
        "short [operations index]",
        "two-phase inbox hash checkpoint",
        "The original direct user request supplies this creation authority",
        "Full filesystem access is capability, not user authority",
        "Before the first intentional write in a turn outside the current Git common repository",
    ),
    "references/operations.md": (
        "[execution.md](execution.md)",
        "[reconciliation.md](reconciliation.md)",
        "[messaging.md](messaging.md)",
        "Never cache codebase reads",
    ),
    "references/execution.md": (
        "complete executable assignment in the native creation prompt",
        "Subagents remain available inside",
        "Inherit the user's configured model, but use cost-safe reasoning",
        "host's equivalent reasoning field",
        "Routine microtasks stay inside the current owner",
        "Use one to three parent-owned subagents when at least two independent, bounded lanes",
        "coordination cost exceeds its value",
    ),
    "references/reconciliation.md": (
        "scan-inbox",
        "ack-inbox",
        "afterCursor",
        "Do not persist or mirror native turns",
        "codex_app__automation_update",
        "codex_app__set_thread_pinned",
        "codex_app__set_thread_archived",
        "codex_app__fork_thread",
        "codex_app__handoff_thread",
        "Never send task registration, acceptance, task-ID assignment",
        "End-of-turn continuation gate",
    ),
    "references/messaging.md": (
        "Project-bound routing",
        "Native task messenger",
        "plain internal message body",
        "Never include or synthesize `<codex_delegation>`",
        "`CREATE_TASK` and `COMPLETE_ACK` are not cross-task message types",
        "Never switch to the collaboration messenger as a fallback",
    ),
    "references/doctor.md": (
        "UNATTENDED_RETURN_PATH",
        "verified absence of the required heartbeat",
        "never receives project paths, task URLs, transcript text, or application files",
        "Deep Review is never scheduled",
        "candidate-only",
    ),
    "references/recovery.md": (
        "inspect that exact owner's native status in the same turn",
        "never ask the user to ping the old task, repeat an exact phrase",
        "The direct request that first exposes the archived owner",
    ),
    "references/maintenance.md": (
        "Before an installation, repair, or Doctor `--apply` writes outside the current repository",
        "A user-approved recurring Doctor may reuse the bounded project inbox targets",
        "Newly discovered projects or external destinations require a fresh notice and approval",
    ),
}
FORBIDDEN_GUIDANCE = (
    "non-executable holding prompt",
    "choose dynamically from the current host catalog",
)


class DoctorError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, child in pairs:
            if key in value:
                raise DoctorError(f"Duplicate JSON key {key!r} in {path}")
            value[key] = child
        return value

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DoctorError(f"Cannot parse {path}: {error}") from error
    if not isinstance(value, dict):
        raise DoctorError(f"Expected a JSON object in {path}")
    return value


def _hook_commands(value: Any) -> list[str]:
    commands: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"command", "commandWindows"} and isinstance(child, str):
                commands.append(child)
            else:
                commands.extend(_hook_commands(child))
    elif isinstance(value, list):
        for child in value:
            commands.extend(_hook_commands(child))
    return commands


def _validated_source(source_plugin: Path) -> tuple[Path, Path]:
    source_plugin = source_plugin.resolve(strict=True)
    manifest = _read_json(source_plugin / ".codex-plugin" / "plugin.json")
    if manifest.get("name") != PLUGIN_NAME:
        raise DoctorError(
            f"Expected plugin name {PLUGIN_NAME!r}, found {manifest.get('name')!r}"
        )
    hooks = _read_json(source_plugin / "hooks" / "hooks.json")
    if not isinstance(hooks.get("hooks"), dict):
        raise DoctorError("Plugin hooks.json has no hooks object")
    session_start = hooks["hooks"].get("SessionStart")
    if not isinstance(session_start, list) or not session_start:
        raise DoctorError("Plugin hooks.json has no SessionStart registration")
    packaged_hook = re.compile(
        rf"\$\{{PLUGIN_ROOT\}}[\\/]+scripts[\\/]+{re.escape(HOOK_NAME)}(?:[\"']|\s|$)"
    )
    if not any(packaged_hook.search(command) for command in _hook_commands(session_start)):
        raise DoctorError("SessionStart does not reference the packaged Coordinator hook")

    skill_source = source_plugin / "skills" / PLUGIN_NAME
    hook_source = source_plugin / "scripts" / HOOK_NAME
    if not (skill_source / "SKILL.md").is_file():
        raise DoctorError(f"Missing source skill: {skill_source / 'SKILL.md'}")
    if not hook_source.is_file():
        raise DoctorError(f"Missing source hook: {hook_source}")
    _validate_capability_contract(skill_source)
    return skill_source, hook_source


def _source_files(skill_source: Path, hook_source: Path) -> list[tuple[str, Path, Path]]:
    mappings: list[tuple[str, Path, Path]] = []
    for source in sorted(skill_source.rglob("*")):
        if source.is_symlink():
            raise DoctorError(f"Symlinks are not supported in the source skill: {source}")
        relative = source.relative_to(skill_source)
        if "__pycache__" in relative.parts or source.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if source.is_file():
            mappings.append(("skill", source, relative))
    mappings.append(("hook", hook_source, Path(HOOK_NAME)))
    return mappings


def _validate_capability_contract(skill_root: Path) -> list[dict[str, str]]:
    contract_path = skill_root / CAPABILITY_CONTRACT
    contract = _read_json(contract_path)
    if contract.get("contractVersion") != CAPABILITY_CONTRACT_VERSION:
        raise DoctorError(
            "Installed Coordinator capability contract is missing or outdated: "
            f"expected {CAPABILITY_CONTRACT_VERSION!r}, found {contract.get('contractVersion')!r}"
        )
    capabilities = contract.get("capabilities")
    if not isinstance(capabilities, dict):
        raise DoctorError("Installed Coordinator capability contract has no capabilities object")
    for name, expected in REQUIRED_CAPABILITIES.items():
        if capabilities.get(name) != expected:
            raise DoctorError(
                f"Installed Coordinator capability {name!r} is stale: "
                f"expected {expected!r}, found {capabilities.get(name)!r}"
            )
    lifecycle = capabilities.get("taskLifecycle")
    if not isinstance(lifecycle, list) or not REQUIRED_TASK_LIFECYCLE.issubset(
        {str(value) for value in lifecycle}
    ):
        raise DoctorError("Installed Coordinator task-lifecycle capability set is incomplete")

    for relative, required_markers in REQUIRED_GUIDANCE.items():
        path = skill_root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise DoctorError(f"Cannot read installed capability guidance {path}: {error}") from error
        for marker in required_markers:
            if marker not in text:
                raise DoctorError(
                    f"Installed Coordinator capability guidance is stale: {relative} lacks {marker!r}"
                )
        for marker in FORBIDDEN_GUIDANCE:
            if marker in text:
                raise DoctorError(
                    f"Installed Coordinator capability guidance is stale: {relative} retains {marker!r}"
                )

    state_tool = skill_root / str(REQUIRED_CAPABILITIES["stateTool"])
    try:
        compile(state_tool.read_text(encoding="utf-8"), str(state_tool), "exec")
    except (OSError, UnicodeError, SyntaxError) as error:
        raise DoctorError(f"Installed Coordinator state helper is invalid: {state_tool}: {error}") from error
    return [
        {
            "name": "skill-capability-contract",
            "status": "passed",
            "detail": str(CAPABILITY_CONTRACT_VERSION),
        },
        {"name": "state-helper-syntax", "status": "passed"},
    ]


def _validate_skill_package(
    skill_root: Path,
    managed_markdown: list[Path],
) -> list[dict[str, str]]:
    skill_path = skill_root / "SKILL.md"
    try:
        skill_text = skill_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise DoctorError(f"Cannot read installed skill {skill_path}: {error}") from error
    frontmatter = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", skill_text, re.DOTALL)
    if not frontmatter or not re.search(
        rf"(?m)^name:\s*{re.escape(PLUGIN_NAME)}\s*$", frontmatter.group(1)
    ):
        raise DoctorError(f"Installed skill has invalid Coordinator frontmatter: {skill_path}")

    capability_checks = _validate_capability_contract(skill_root)
    checked_links = 0
    for markdown in sorted(managed_markdown):
        try:
            text = markdown.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise DoctorError(f"Cannot read installed skill document {markdown}: {error}") from error
        for raw_target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = raw_target.strip().strip("<>").split("#", 1)[0].strip()
            if not target or target.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            resolved = (markdown.parent / target).resolve(strict=False)
            try:
                resolved.relative_to(skill_root.resolve(strict=False))
            except ValueError as error:
                raise DoctorError(f"Installed skill link escapes its package: {markdown} -> {target}") from error
            if not resolved.is_file():
                raise DoctorError(f"Installed skill link is missing: {markdown} -> {target}")
            checked_links += 1
    return capability_checks + [
        {"name": "skill-frontmatter", "status": "passed"},
        {"name": "skill-links", "status": "passed", "detail": str(checked_links)},
    ]


def _validate_installed_hook(hook_path: Path) -> list[dict[str, str]]:
    try:
        hook_text = hook_path.read_text(encoding="utf-8")
        compile(hook_text, str(hook_path), "exec")
    except (OSError, UnicodeError, SyntaxError) as error:
        raise DoctorError(f"Installed SessionStart hook is invalid: {hook_path}: {error}") from error

    try:
        with tempfile.TemporaryDirectory(prefix="codex-coordinator-doctor-") as directory:
            completed = subprocess.run(
                [sys.executable, str(hook_path)],
                input=json.dumps({"cwd": directory, "session_id": "doctor-smoke"}),
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=10,
                check=False,
            )
    except (OSError, subprocess.SubprocessError) as error:
        raise DoctorError(f"Installed SessionStart hook could not run: {hook_path}: {error}") from error
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "no output").strip()
        raise DoctorError(
            f"Installed SessionStart hook smoke check failed with {completed.returncode}: {detail}"
        )
    return [
        {"name": "hook-syntax", "status": "passed"},
        {"name": "hook-smoke", "status": "passed"},
    ]


def _validate_installation(
    skill_root: Path,
    hook_path: Path,
    managed_markdown: list[Path],
) -> list[dict[str, str]]:
    return _validate_skill_package(skill_root, managed_markdown) + _validate_installed_hook(hook_path)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass


def _mermaid_label(value: Any) -> str:
    """Return a single safe Mermaid label without exposing raw report structure."""
    compact = " ".join(str(value).replace("\r", " ").replace("\n", " ").split())
    return html.escape(compact, quote=True)


def _mermaid_class(value: Any) -> str:
    state = str(value).strip().lower()
    return state if state in {"current", "drift", "missing", "updated", "passed", "error"} else "unknown"


def _parent_state(report: dict[str, Any], kind: str) -> str:
    states = [
        _mermaid_class(item.get("state"))
        for item in report.get("files", [])
        if isinstance(item, dict) and item.get("kind") == kind
    ]
    check_states = [
        _mermaid_class(check.get("status"))
        for check in report.get("installationChecks", [])
        if isinstance(check, dict)
        and (str(check.get("name", "")).startswith("hook-") == (kind == "hook"))
    ]
    states.extend(check_states)
    for candidate in ("error", "missing", "drift", "updated", "unknown"):
        if candidate in states:
            return candidate
    return "current"


def render_mermaid(report: dict[str, Any]) -> str:
    """Project Doctor's verified JSON result into a dependency-free Mermaid map."""
    status = _mermaid_class(report.get("status"))
    changed = report.get("changedFiles", 0)
    if not isinstance(changed, int) or isinstance(changed, bool) or changed < 0:
        changed = 0

    if status == "current":
        outcome = "CURRENT<br/>Managed files and checks passed"
    elif status == "updated":
        outcome = f"UPDATED<br/>{changed} managed file(s) repaired"
    elif status == "drift":
        outcome = f"DRIFT<br/>{changed} managed file(s) differ"
    elif status == "error":
        outcome = "ERROR<br/>See Doctor JSON for the exact cause"
    else:
        outcome = "UNKNOWN<br/>Doctor returned an unsupported state"

    lines = [
        "flowchart TD",
        '  doctor["Coordinator Doctor"]',
        '  source["Trusted plugin package"]',
        f'  outcome{{"{outcome}"}}',
        "  doctor --> source",
    ]

    if status == "error":
        lines.append("  source --> outcome")
    else:
        lines.extend(
            [
                '  skill["Installed global skill"]',
                '  hook["SessionStart hook"]',
                "  source --> skill",
                "  source --> hook",
                "  skill --> outcome",
                "  hook --> outcome",
            ]
        )
        for index, item in enumerate(report.get("files", []), start=1):
            if not isinstance(item, dict):
                continue
            kind = "hook" if item.get("kind") == "hook" else "skill"
            state = _mermaid_class(item.get("state"))
            managed_path = item.get("managedPath") or Path(str(item.get("target", "file"))).name
            label = _mermaid_label(managed_path)
            node = f"file_{index}"
            lines.append(f'  {node}["{label}<br/>{state.upper()}"]')
            lines.append(f"  {kind} --> {node}")
            lines.append(f"  class {node} {state}")

        for index, check in enumerate(report.get("installationChecks", []), start=1):
            if not isinstance(check, dict):
                continue
            name = str(check.get("name", "unnamed-check"))
            parent = "hook" if name.startswith("hook-") else "skill"
            state = _mermaid_class(check.get("status"))
            label = _mermaid_label(name)
            detail = check.get("detail")
            detail_label = f"<br/>{_mermaid_label(detail)}" if detail is not None else ""
            node = f"check_{index}"
            lines.append(f'  {node}["{label}{detail_label}<br/>{state.upper()}"]')
            lines.append(f"  {parent} --> {node}")
            lines.append(f"  class {node} {state}")

        lines.append(f"  class skill {_parent_state(report, 'skill')}")
        lines.append(f"  class hook {_parent_state(report, 'hook')}")

    lines.extend(
        [
            f"  class outcome {status}",
            "  classDef current fill:#123d2b,stroke:#56d68b,color:#ffffff",
            "  classDef passed fill:#123d2b,stroke:#56d68b,color:#ffffff",
            "  classDef updated fill:#12344d,stroke:#65c7ff,color:#ffffff",
            "  classDef drift fill:#4a3512,stroke:#f0b44d,color:#ffffff",
            "  classDef missing fill:#4d1f28,stroke:#ff6b7a,color:#ffffff",
            "  classDef error fill:#4d1f28,stroke:#ff6b7a,color:#ffffff",
            "  classDef unknown fill:#2f3340,stroke:#9aa4b2,color:#ffffff",
        ]
    )
    return "\n".join(lines) + "\n"


def write_mermaid_report(path: Path, report: dict[str, Any]) -> str:
    """Atomically write a visual projection of a completed Doctor report."""
    _atomic_write(path, render_mermaid(report).encode("utf-8"))
    return str(path.resolve(strict=False))


def sync_installation(
    source_plugin: Path,
    skill_root: Path,
    hook_path: Path,
    *,
    apply: bool,
) -> dict[str, Any]:
    resolved_skill_root = skill_root.resolve(strict=False)
    resolved_hook_path = hook_path.resolve(strict=False)
    try:
        resolved_hook_path.relative_to(resolved_skill_root)
    except ValueError:
        pass
    else:
        raise DoctorError(
            "The SessionStart hook destination must not overlap the installed skill directory"
        )
    try:
        resolved_skill_root.relative_to(resolved_hook_path)
    except ValueError:
        pass
    else:
        raise DoctorError(
            "The installed skill directory must not overlap the SessionStart hook destination"
        )

    skill_source, hook_source = _validated_source(source_plugin)
    files: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []
    changed = 0
    installation_checks: list[dict[str, str]] = []

    for kind, source, relative in _source_files(skill_source, hook_source):
        target = skill_root / relative if kind == "skill" else hook_path
        source_bytes = source.read_bytes()
        source_hash = _sha256(source_bytes)
        try:
            target_bytes = target.read_bytes()
        except FileNotFoundError:
            target_bytes = None
        except OSError as error:
            raise DoctorError(f"Cannot read installation target {target}: {error}") from error

        before = "missing" if target_bytes is None else (
            "current" if _sha256(target_bytes) == source_hash else "drift"
        )
        state = before
        if before != "current":
            changed += 1
        files.append(
            {
                "kind": kind,
                "managedPath": relative.as_posix(),
                "source": str(source),
                "target": str(target),
                "before": before,
                "state": state,
                "sha256": source_hash,
            }
        )
        planned.append(
            {
                "kind": kind,
                "relative": relative,
                "target": target,
                "sourceBytes": source_bytes,
                "sourceHash": source_hash,
                "targetBytes": target_bytes,
                "before": before,
            }
        )

    managed_markdown = [
        skill_root / item["relative"]
        for item in planned
        if item["kind"] == "skill" and item["relative"].suffix.lower() == ".md"
    ]

    if apply and changed:
        applied: list[dict[str, Any]] = []
        try:
            for item in planned:
                if item["before"] == "current":
                    continue
                _atomic_write(item["target"], item["sourceBytes"])
                applied.append(item)
            for item in applied:
                if _sha256(item["target"].read_bytes()) != item["sourceHash"]:
                    raise DoctorError(f"Installation verification failed for {item['target']}")
            installation_checks = _validate_installation(skill_root, hook_path, managed_markdown)
        except (DoctorError, OSError) as error:
            rollback_errors: list[str] = []
            for item in reversed(applied):
                try:
                    if item["targetBytes"] is None:
                        item["target"].unlink(missing_ok=True)
                    else:
                        _atomic_write(item["target"], item["targetBytes"])
                except OSError as rollback_error:
                    rollback_errors.append(f"{item['target']}: {rollback_error}")
            detail = ""
            if rollback_errors:
                detail = "; rollback also failed for " + "; ".join(rollback_errors)
            raise DoctorError(f"Installation update failed and was rolled back: {error}{detail}") from error
        for file in files:
            if file["before"] != "current":
                file["state"] = "updated"
    elif not changed:
        installation_checks = _validate_installation(skill_root, hook_path, managed_markdown)

    return {
        "status": "updated" if apply and changed else ("drift" if changed else "current"),
        "sourcePlugin": str(source_plugin.resolve(strict=True)),
        "skillRoot": str(skill_root.resolve(strict=False)),
        "hookPath": str(hook_path.resolve(strict=False)),
        "changedFiles": changed,
        "files": files,
        "installationChecks": installation_checks,
        "repairScope": "installed global skill and exact SessionStart hook",
        "note": "Unexpected installation files are preserved; Doctor never edits managed plugin caches or project files.",
    }


def _default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repair and validate the installed Codex Coordinator runtime from a trusted package."
    )
    parser.add_argument(
        "--source-plugin",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to the trusted plugins/codex-coordinator update package.",
    )
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path.home() / ".agents" / "skills" / PLUGIN_NAME,
        help="Installed global skill directory.",
    )
    parser.add_argument(
        "--hook-path",
        type=Path,
        default=_default_codex_home() / "hooks" / HOOK_NAME,
        help="Installed legacy/global SessionStart hook path.",
    )
    parser.add_argument(
        "--mermaid-out",
        type=Path,
        help="Write an optional Mermaid .mmd projection; JSON and exit status remain authoritative.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print only status and aggregate check counts without paths or managed-file detail.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Report drift without writing (default).")
    mode.add_argument("--apply", action="store_true", help="Atomically update drifted targets.")
    args = parser.parse_args(argv)

    exit_code = 0
    try:
        report = sync_installation(
            args.source_plugin,
            args.skill_root,
            args.hook_path,
            apply=bool(args.apply),
        )
    except (DoctorError, OSError) as error:
        report = {"status": "error", "error": str(error)}
        exit_code = 1

    if args.mermaid_out is not None:
        try:
            report["mermaidPath"] = write_mermaid_report(args.mermaid_out, report)
            report["mermaidNote"] = (
                "Visual projection only; Doctor JSON, exit status, and checks remain authoritative."
            )
        except OSError as error:
            report["mermaidError"] = str(error)
            exit_code = 1

    output = report
    if args.compact:
        output = {
            "status": report.get("status", "error"),
            "changedFiles": int(report.get("changedFiles") or 0),
            "checksPassed": sum(
                check.get("status") == "passed"
                for check in report.get("installationChecks", [])
                if isinstance(check, dict)
            ),
        }
        if report.get("error"):
            output["error"] = report["error"]
    print(json.dumps(output, indent=None if args.compact else 2, separators=(",", ":") if args.compact else None))
    if exit_code:
        return exit_code
    if not args.apply and report["status"] == "drift":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
