from __future__ import annotations

import argparse
import hashlib
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
CAPABILITY_CONTRACT_VERSION = 3
REQUIRED_CAPABILITIES: dict[str, Any] = {
    "workerCreation": "full-assignment-first-turn",
    "coordinatorRole": "control-first",
    "monitoring": "heartbeat-with-single-wake-fallback",
    "modelDefault": "inherit-unless-user-overrides",
    "reasoningDefault": "low-or-medium",
    "stateTool": "scripts/coordination_state.py",
    "subagents": "allowed-parent-owned",
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
        "set reasoning explicitly to `low`",
        "Subagents remain available as parent-owned helpers",
        "scripts/coordination_state.py",
    ),
    "references/operations.md": (
        "complete executable assignment in the native creation prompt",
        "Subagents remain available inside",
        "codex_app__automation_update",
        "codex_app__set_thread_pinned",
        "codex_app__set_thread_archived",
        "codex_app__fork_thread",
        "codex_app__handoff_thread",
        "Inherit the user's configured model, but use cost-safe reasoning",
        "host's equivalent reasoning field",
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
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Report drift without writing (default).")
    mode.add_argument("--apply", action="store_true", help="Atomically update drifted targets.")
    args = parser.parse_args(argv)

    try:
        report = sync_installation(
            args.source_plugin,
            args.skill_root,
            args.hook_path,
            apply=bool(args.apply),
        )
    except (DoctorError, OSError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, indent=2))
        return 1

    print(json.dumps(report, indent=2))
    if not args.apply and report["status"] == "drift":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
