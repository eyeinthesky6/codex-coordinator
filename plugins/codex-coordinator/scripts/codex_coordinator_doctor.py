from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PLUGIN_NAME = "codex-coordinator"
HOOK_NAME = "codex_coordinator_session_start.py"
CAPABILITY_CONTRACT = "capabilities.json"
CAPABILITY_CONTRACT_VERSION = 21
RECEIPT_SCHEMA_VERSION = 2
RECEIPT_MANIFEST_KEY = "integrityReceipt"
PACKAGE_STATE_KEY = "packageState"
RELEASE_PACKAGE_STATE = "release"
INSTALLATION_KINDS = {"auto", "manual", "marketplace"}
RELEASE_VERSION = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
REQUIRED_CAPABILITIES: dict[str, Any] = {
    "workerCreation": "full-assignment-first-turn",
    "coordinatorRole": "control-first",
    "doctorDiagnostics": "json-with-optional-mermaid",
    "doctorProjectScan": "deterministic-structured-state-zero-model",
    "doctorSemanticReview": "user-triggered-allowlisted-low-candidate-only",
    "monitoring": "enabled-repository-persistent-heartbeat",
    "repositoryLifecycle": "active-by-default-after-enablement",
    "taskCoverage": "all-same-repository-tasks-by-default",
    "taskExclusions": "direct-user-only",
    "pauseBehavior": "report-only-no-control-actions",
    "idleBehavior": "retain-pinned-accepting-coordinator",
    "userStateReporting": "mode-and-exclusions-always-visible",
    "deliverySummary": "complete-ledger-sections-every-user-visible-final",
    "providerMonitoring": "bounded-read-reconcile-at-start-change-closure",
    "providerMutationConsent": "exact-current-consent-immutable-target-revalidation",
    "scheduledTaskReconciliation": "exact-project-binding-major-change-direct-decision",
    "installedCoreIntegrity": "external-receipt-pin-marketplace-reinstall-manual-rollback",
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
    "pythonRuntimeBootstrap": "bounded-machine-discovery-informed-install",
    "lifecycleCleanup": "dry-run-first-history-preserving",
    "globalUninstall": "verified-project-index-no-drive-scan",
    "worktreeSelection": "coordinator-selected-bounded-when-beneficial",
    "waitingClassification": "canonical-evidence-only",
    "delegationDecision": "reuse-first-recorded",
    "taskTitlePolicy": "rename-generic-once-preserve-user-title",
    "historicalTaskReconciliation": "current-goal-authority-and-disposition",
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
        "one repository heartbeat",
        "verify exactly one repository heartbeat",
        "Every same-repository Codex task is managed by default",
        "Only a direct user instruction may add or remove",
        "A user pause switches to `REPORT_ONLY`",
        "workload idle never unregisters the Coordinator",
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
        "record the reuse-first choice",
        "one rename of a generated generic task title",
        "dry-run-first and preserve project history",
        "Mark unclear relevance or authority `AWAITING_USER_DECISION`",
        "count material historical items closed, continued, deferred or not needed",
        "At goal start, after material Git changes, and before closure",
        "Any provider mutation requires exact current user consent",
        "At goal start, after material task or automation changes, and before closure",
        "Before every user-visible Coordinator final response",
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
        "Record the delegation decision before ordinary implementation starts",
        "Rename a generated generic title once",
        "Coordinator may place an independent writer in a bounded linked worktree",
        "Carry forward the exact unmet outcome",
        "Do not make the user inspect old task windows",
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
        "GitHub monitoring and provider consent",
        "exact current user consent",
        "return the exact provider receipt",
        "Project-related scheduled-task reconciliation",
        "Record a direct user decision before any major scheduled-task change",
        "Before every user-visible Coordinator final response",
        "done work, pending work, blockers or decisions, next actions, and the full-goal verdict",
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
        "immutable package receipt",
        "marketplace-managed",
        "last-known-good",
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
        "Deactivation, uninstall, and purge",
        "global-plan --codex-home <codex-home>",
        "never scans an entire drive",
    ),
    "references/installation.md": (
        "Project deactivation and reactivation",
        "project deactivate --project-root <primary-worktree>",
        "project reactivate --project-root <primary-worktree>",
        "Project purge is not opt-out",
    ),
}
FORBIDDEN_GUIDANCE = (
    "non-executable holding prompt",
    "choose dynamically from the current host catalog",
)


class DoctorError(RuntimeError):
    pass


class RepairFailed(DoctorError):
    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message)
        self.report = report


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_redirecting_components(path: Path) -> None:
    absolute = _absolute_path(path)
    components = (absolute, *absolute.parents)
    for component in reversed(components):
        try:
            metadata = os.lstat(component)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise DoctorError(
                f"Cannot inspect installation target component {component}: {error}"
            ) from error
        attributes = getattr(metadata, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if stat.S_ISLNK(metadata.st_mode) or (
            reparse_flag and attributes & reparse_flag
        ):
            raise DoctorError(
                f"Installation target contains a symlink or reparse-point component: {component}"
            )


def _canonical_destination(path: Path) -> Path:
    absolute = _absolute_path(path)
    _reject_redirecting_components(absolute)
    return absolute.resolve(strict=False)


def _assert_installed_target(
    target: Path,
    *,
    kind: str,
    canonical_skill_root: Path,
    canonical_hook_path: Path,
) -> Path:
    absolute = _absolute_path(target)
    _reject_redirecting_components(absolute)
    resolved = absolute.resolve(strict=False)
    if kind == "skill":
        try:
            resolved.relative_to(canonical_skill_root)
        except ValueError as error:
            raise DoctorError(
                f"Installed skill target escapes its canonical root: {target}"
            ) from error
    elif kind == "hook":
        if resolved != canonical_hook_path:
            raise DoctorError(
                "SessionStart hook target does not match its authorised canonical path"
            )
    else:
        raise DoctorError(f"Unsupported installed target kind: {kind!r}")
    return absolute


def _parse_json(path: Path, raw: bytes) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, child in pairs:
            if key in value:
                raise DoctorError(f"Duplicate JSON key {key!r} in {path}")
            value[key] = child
        return value

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DoctorError(f"Cannot parse {path}: {error}") from error
    if not isinstance(value, dict):
        raise DoctorError(f"Expected a JSON object in {path}")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise DoctorError(f"Cannot read {path}: {error}") from error
    return _parse_json(path, raw)


def _validate_expected_release(
    expected_receipt_sha256: str | None,
    expected_package_version: str | None,
    *,
    required: bool,
) -> tuple[str | None, str | None]:
    if expected_receipt_sha256 is None and expected_package_version is None and not required:
        return None, None
    if expected_receipt_sha256 is None or expected_package_version is None:
        raise DoctorError(
            "Manual package trust requires both an expected package version and an expected receipt SHA-256 from separate release metadata"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", expected_receipt_sha256):
        raise DoctorError("Expected receipt SHA-256 is malformed")
    if (
        len(expected_package_version) > 100
        or not RELEASE_VERSION.fullmatch(expected_package_version)
        or expected_package_version == "0.0.0-unreleased"
    ):
        raise DoctorError("Expected package version is malformed or unreleased")
    return expected_receipt_sha256, expected_package_version


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


def _safe_package_path(source_plugin: Path, raw: Any, *, field: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise DoctorError(f"Trusted package receipt has no {field}")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise DoctorError(f"Trusted package receipt has unsafe {field}: {raw!r}")
    candidate = source_plugin / relative
    if candidate.is_symlink():
        raise DoctorError(f"Trusted package receipt cannot manage a symlink: {raw!r}")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(source_plugin)
    except ValueError as error:
        raise DoctorError(f"Trusted package receipt {field} escapes the package: {raw!r}") from error
    return resolved


def _reject_dirty_developer_source(source_plugin: Path) -> None:
    has_git_marker = any(
        (current / ".git").exists() for current in (source_plugin, *source_plugin.parents)
    )
    try:
        root = subprocess.run(
            ["git", "-C", str(source_plugin), "rev-parse", "--show-toplevel"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        if has_git_marker:
            raise DoctorError(f"Cannot verify trusted package Git state: {error}") from error
        return
    if root.returncode != 0:
        if has_git_marker:
            raise DoctorError("Cannot verify trusted package Git state")
        return
    try:
        repository = Path(root.stdout.strip()).resolve(strict=True)
        relative = source_plugin.relative_to(repository)
    except (OSError, ValueError):
        raise DoctorError("Trusted package identity is ambiguous inside its Git repository")
    try:
        status = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                relative.as_posix(),
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise DoctorError(f"Cannot verify trusted package Git state: {error}") from error
    if status.returncode != 0:
        raise DoctorError("Cannot verify trusted package Git state")
    if status.stdout.strip():
        raise DoctorError(
            "Trusted repair source is a dirty developer checkout; use an immutable release package"
        )


def _validated_source(
    source_plugin: Path,
    *,
    expected_receipt_sha256: str | None,
    expected_package_version: str | None,
) -> tuple[Path, Path, dict[str, Any], list[dict[str, Any]]]:
    source_plugin = source_plugin.resolve(strict=True)
    manifest = _read_json(source_plugin / ".codex-plugin" / "plugin.json")
    if manifest.get("name") != PLUGIN_NAME:
        raise DoctorError(
            f"Expected plugin name {PLUGIN_NAME!r}, found {manifest.get('name')!r}"
        )
    receipt_name = manifest.get(RECEIPT_MANIFEST_KEY)
    receipt_path = _safe_package_path(
        source_plugin, receipt_name, field=RECEIPT_MANIFEST_KEY
    )
    try:
        receipt_bytes = receipt_path.read_bytes()
    except OSError as error:
        raise DoctorError(f"Cannot read trusted package receipt: {error}") from error
    receipt_sha256 = _sha256(receipt_bytes)
    if (
        expected_receipt_sha256 is not None
        and receipt_sha256 != expected_receipt_sha256
    ):
        raise DoctorError("Trusted package receipt does not match the expected release pin")
    receipt = _parse_json(receipt_path, receipt_bytes)
    if receipt.get("schemaVersion") != RECEIPT_SCHEMA_VERSION:
        raise DoctorError(
            "Trusted package receipt schema is unsupported: "
            f"expected {RECEIPT_SCHEMA_VERSION}, found {receipt.get('schemaVersion')!r}"
        )
    if receipt.get("pluginName") != PLUGIN_NAME:
        raise DoctorError("Trusted package receipt has the wrong plugin identity")
    if manifest.get(PACKAGE_STATE_KEY) != RELEASE_PACKAGE_STATE:
        raise DoctorError("Trusted package metadata is not a release package")
    if receipt.get(PACKAGE_STATE_KEY) != RELEASE_PACKAGE_STATE:
        raise DoctorError("Trusted package receipt is not a release receipt")
    if receipt.get("packageVersion") != manifest.get("version"):
        raise DoctorError("Trusted package receipt version does not match plugin metadata")
    if (
        not isinstance(receipt.get("packageVersion"), str)
        or not RELEASE_VERSION.fullmatch(receipt["packageVersion"])
        or receipt["packageVersion"] == "0.0.0-unreleased"
    ):
        raise DoctorError("Trusted package receipt has a malformed or unreleased version")
    if (
        expected_package_version is not None
        and receipt.get("packageVersion") != expected_package_version
    ):
        raise DoctorError("Trusted package version does not match the expected release version")
    package_id = receipt.get("packageId")
    expected_package_id = (
        f"{PLUGIN_NAME}-package@{receipt.get('packageVersion')}"
        f"+contract{CAPABILITY_CONTRACT_VERSION}"
    )
    if package_id != expected_package_id:
        raise DoctorError("Trusted package receipt has the wrong release identity")

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
    entries = receipt.get("managedFiles")
    if not isinstance(entries, list) or not entries:
        raise DoctorError("Trusted package receipt has no managed files")

    normalized: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    seen_targets: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise DoctorError("Trusted package receipt contains a malformed managed-file entry")
        kind = entry.get("kind")
        if kind not in {"skill", "hook"}:
            raise DoctorError(f"Trusted package receipt has unsupported target kind {kind!r}")
        source = _safe_package_path(source_plugin, entry.get("sourcePath"), field="sourcePath")
        source_key = source.relative_to(source_plugin).as_posix()
        managed = Path(str(entry.get("managedPath", "")))
        if not managed.parts or managed.is_absolute() or ".." in managed.parts:
            raise DoctorError("Trusted package receipt has an unsafe managedPath")
        if kind == "hook" and managed != Path(HOOK_NAME):
            raise DoctorError("Trusted package receipt declares an unexpected hook target")
        target_key = (str(kind), managed.as_posix())
        if source_key in seen_sources or target_key in seen_targets:
            raise DoctorError("Trusted package receipt contains a duplicate managed-file mapping")
        seen_sources.add(source_key)
        seen_targets.add(target_key)
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise DoctorError(f"Trusted package receipt has an invalid hash for {source_key}")
        try:
            source_bytes = source.read_bytes()
        except OSError as error:
            raise DoctorError(f"Trusted package file is missing or unreadable: {source_key}") from error
        if _sha256(source_bytes) != digest:
            raise DoctorError(f"Trusted package receipt hash mismatch for {source_key}")
        normalized.append(
            {
                "kind": kind,
                "source": source,
                "relative": managed,
                "sourceBytes": source_bytes,
                "sourceHash": digest,
            }
        )

    actual_sources = {
        path.relative_to(source_plugin).as_posix()
        for path in skill_source.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.relative_to(skill_source).parts
        and path.suffix.lower() not in {".pyc", ".pyo"}
    }
    actual_sources.add(hook_source.relative_to(source_plugin).as_posix())
    if actual_sources != seen_sources:
        missing = sorted(actual_sources - seen_sources)
        extra = sorted(seen_sources - actual_sources)
        raise DoctorError(
            "Trusted package receipt does not exactly declare the managed package files: "
            f"missing={missing}, unexpected={extra}"
        )
    _reject_dirty_developer_source(source_plugin)
    receipt_summary = {
        "schemaVersion": RECEIPT_SCHEMA_VERSION,
        "pluginName": PLUGIN_NAME,
        "packageVersion": receipt.get("packageVersion"),
        "packageId": receipt.get("packageId"),
        "sha256": receipt_sha256,
        "managedFileCount": len(normalized),
    }
    return skill_source, hook_source, receipt_summary, normalized


def _source_files(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda item: (str(item["kind"]), item["relative"].as_posix()))


def _validate_capability_contract(
    skill_root: Path,
    assert_target: Any | None = None,
) -> list[dict[str, str]]:
    contract_path = skill_root / CAPABILITY_CONTRACT
    if assert_target is not None:
        contract_path = assert_target(contract_path)
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
        if assert_target is not None:
            path = assert_target(path)
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
    if assert_target is not None:
        state_tool = assert_target(state_tool)
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
    assert_target: Any | None = None,
) -> list[dict[str, str]]:
    canonical_skill_root = (
        assert_target(skill_root).resolve(strict=False)
        if assert_target is not None
        else skill_root.resolve(strict=False)
    )
    skill_path = skill_root / "SKILL.md"
    if assert_target is not None:
        skill_path = assert_target(skill_path)
    try:
        skill_text = skill_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise DoctorError(f"Cannot read installed skill {skill_path}: {error}") from error
    frontmatter = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", skill_text, re.DOTALL)
    if not frontmatter or not re.search(
        rf"(?m)^name:\s*{re.escape(PLUGIN_NAME)}\s*$", frontmatter.group(1)
    ):
        raise DoctorError(f"Installed skill has invalid Coordinator frontmatter: {skill_path}")

    capability_checks = _validate_capability_contract(skill_root, assert_target)
    checked_links = 0
    for markdown in sorted(managed_markdown):
        if assert_target is not None:
            markdown = assert_target(markdown)
        try:
            text = markdown.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise DoctorError(f"Cannot read installed skill document {markdown}: {error}") from error
        for raw_target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = raw_target.strip().strip("<>").split("#", 1)[0].strip()
            if not target or target.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            resolved = markdown.parent / target
            if assert_target is not None:
                resolved = assert_target(resolved)
            resolved = resolved.resolve(strict=False)
            try:
                resolved.relative_to(canonical_skill_root)
            except ValueError as error:
                raise DoctorError(f"Installed skill link escapes its package: {markdown} -> {target}") from error
            if not resolved.is_file():
                raise DoctorError(f"Installed skill link is missing: {markdown} -> {target}")
            checked_links += 1
    return capability_checks + [
        {"name": "skill-frontmatter", "status": "passed"},
        {"name": "skill-links", "status": "passed", "detail": str(checked_links)},
    ]


def _validate_installed_hook(
    hook_path: Path,
    assert_target: Any | None = None,
) -> list[dict[str, str]]:
    if assert_target is not None:
        hook_path = assert_target(hook_path)
    try:
        hook_text = hook_path.read_text(encoding="utf-8")
        compile(hook_text, str(hook_path), "exec")
    except (OSError, UnicodeError, SyntaxError) as error:
        raise DoctorError(f"Installed SessionStart hook is invalid: {hook_path}: {error}") from error

    try:
        if assert_target is not None:
            hook_path = assert_target(hook_path)
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
    assert_skill_target: Any | None = None,
    assert_hook_target: Any | None = None,
) -> list[dict[str, str]]:
    return _validate_skill_package(
        skill_root, managed_markdown, assert_skill_target
    ) + _validate_installed_hook(hook_path, assert_hook_target)


def _atomic_write(path: Path, data: bytes, assert_safe: Any | None = None) -> None:
    if assert_safe is not None:
        path = assert_safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if assert_safe is not None:
        path = assert_safe(path)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        if assert_safe is not None:
            path = assert_safe(path)
        Path(temporary_name).replace(path)
    finally:
        if temporary_name:
            if assert_safe is not None:
                assert_safe(path)
            Path(temporary_name).unlink(missing_ok=True)


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


def _path_in_plugin_cache(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    lowered = [part.casefold() for part in resolved.parts]
    for index in range(len(lowered) - 1):
        if lowered[index : index + 2] == ["plugins", "cache"]:
            return True
    return False


def _path_lexically_in_plugin_cache(path: Path) -> bool:
    lowered = [part.casefold() for part in _absolute_path(path).parts]
    return any(
        lowered[index : index + 2] == ["plugins", "cache"]
        for index in range(len(lowered) - 1)
    )


def _looks_marketplace_managed(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    if _path_in_plugin_cache(resolved):
        return True
    return any(
        (current / ".codex-plugin" / "plugin.json").is_file()
        for current in (resolved, *resolved.parents)
    )


def _installation_kind(
    source_plugin: Path, skill_root: Path, hook_path: Path, requested: str
) -> str:
    if requested not in INSTALLATION_KINDS:
        raise DoctorError(f"Unsupported installation kind: {requested!r}")
    if requested != "auto":
        return requested
    if (
        _path_in_plugin_cache(source_plugin)
        or _looks_marketplace_managed(skill_root)
        or _looks_marketplace_managed(hook_path)
    ):
        return "marketplace"
    return "manual"


def _rollback_report(
    *,
    files: list[dict[str, Any]],
    receipt: dict[str, Any],
    installation_kind: str,
    changed: int,
    error: Exception,
    rollback_errors: list[str],
) -> dict[str, Any]:
    restored = not rollback_errors
    return {
        "status": "error",
        "integrityState": "local_modification_detected",
        "recoveryState": (
            "repair_failed_last_good_restored" if restored else "manual_action_required"
        ),
        "installationKind": installation_kind,
        "changedFiles": changed,
        "files": files,
        "installationChecks": [],
        "trustedReceipt": receipt,
        "rollback": {
            "attempted": True,
            "lastGoodRestored": restored,
            "errors": rollback_errors,
        },
        "error": str(error),
        "repairScope": "declared managed files only",
        "note": (
            "The attempted manual repair failed; all touched managed files were restored."
            if restored
            else "The attempted manual repair and last-good restore both failed; manual action is required."
        ),
    }


def sync_installation(
    source_plugin: Path,
    skill_root: Path,
    hook_path: Path,
    *,
    apply: bool,
    installation_kind: str = "auto",
    expected_receipt_sha256: str | None = None,
    expected_package_version: str | None = None,
) -> dict[str, Any]:
    if installation_kind not in INSTALLATION_KINDS:
        raise DoctorError(f"Unsupported installation kind: {installation_kind!r}")
    known_marketplace = installation_kind == "marketplace" or (
        installation_kind == "auto"
        and (
            _path_in_plugin_cache(source_plugin)
            or _path_lexically_in_plugin_cache(skill_root)
            or _path_lexically_in_plugin_cache(hook_path)
        )
    )
    expected_receipt_sha256, expected_package_version = _validate_expected_release(
        expected_receipt_sha256,
        expected_package_version,
        required=not known_marketplace,
    )
    try:
        skill_source, hook_source, trusted_receipt, source_entries = _validated_source(
            source_plugin,
            expected_receipt_sha256=expected_receipt_sha256,
            expected_package_version=expected_package_version,
        )
    except DoctorError as error:
        if not known_marketplace:
            raise
        return {
            "status": "error",
            "integrityState": "local_modification_detected",
            "recoveryState": "reinstall_required",
            "installationKind": "marketplace",
            "changedFiles": 0,
            "files": [],
            "installationChecks": [],
            "error": str(error),
            "repairScope": "none; marketplace-managed files are read-only to Doctor",
            "note": (
                "Use the supported Codex plugin update or reinstall path. "
                "Doctor never rewrites marketplace-managed cache files directly."
            ),
        }
    canonical_skill_root = _canonical_destination(skill_root)
    canonical_hook_path = _canonical_destination(hook_path)

    def assert_skill_target(path: Path) -> Path:
        return _assert_installed_target(
            path,
            kind="skill",
            canonical_skill_root=canonical_skill_root,
            canonical_hook_path=canonical_hook_path,
        )

    def assert_hook_target(path: Path) -> Path:
        return _assert_installed_target(
            path,
            kind="hook",
            canonical_skill_root=canonical_skill_root,
            canonical_hook_path=canonical_hook_path,
        )

    assert_skill_target(skill_root)
    assert_hook_target(hook_path)
    resolved_skill_root = canonical_skill_root
    resolved_hook_path = canonical_hook_path
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

    kind = _installation_kind(source_plugin, skill_root, hook_path, installation_kind)
    files: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []
    changed = 0
    installation_checks: list[dict[str, str]] = []

    for source_entry in _source_files(source_entries):
        file_kind = source_entry["kind"]
        source = source_entry["source"]
        relative = source_entry["relative"]
        target = skill_root / relative if file_kind == "skill" else hook_path
        assert_target = assert_skill_target if file_kind == "skill" else assert_hook_target
        target = assert_target(target)
        source_bytes = source_entry["sourceBytes"]
        source_hash = source_entry["sourceHash"]
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
                "kind": file_kind,
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
                "kind": file_kind,
                "relative": relative,
                "target": target,
                "sourceBytes": source_bytes,
                "sourceHash": source_hash,
                "targetBytes": target_bytes,
                "before": before,
                "assertTarget": assert_target,
            }
        )

    managed_markdown = [
        skill_root / item["relative"]
        for item in planned
        if item["kind"] == "skill" and item["relative"].suffix.lower() == ".md"
    ]

    if kind == "marketplace" and changed:
        return {
            "status": "drift",
            "integrityState": "local_modification_detected",
            "recoveryState": "reinstall_required",
            "installationKind": kind,
            "sourcePlugin": str(source_plugin.resolve(strict=True)),
            "skillRoot": str(canonical_skill_root),
            "hookPath": str(canonical_hook_path),
            "changedFiles": changed,
            "files": files,
            "installationChecks": [],
            "trustedReceipt": trusted_receipt,
            "repairScope": "none; marketplace-managed files are read-only to Doctor",
            "note": (
                "Use the supported Codex plugin update or reinstall path. "
                "Doctor never rewrites marketplace-managed cache files directly."
            ),
            "error": "Marketplace-managed installation drift requires plugin update or reinstall.",
        }

    if apply and changed:
        applied: list[dict[str, Any]] = []
        try:
            for item in planned:
                if item["before"] == "current":
                    continue
                item["assertTarget"](item["target"])
                _atomic_write(
                    item["target"], item["sourceBytes"], item["assertTarget"]
                )
                applied.append(item)
            for item in applied:
                item["assertTarget"](item["target"])
                if _sha256(item["target"].read_bytes()) != item["sourceHash"]:
                    raise DoctorError(f"Installation verification failed for {item['target']}")
            installation_checks = _validate_installation(
                skill_root,
                hook_path,
                managed_markdown,
                assert_skill_target,
                assert_hook_target,
            )
        except (DoctorError, OSError) as error:
            rollback_errors: list[str] = []
            for item in reversed(applied):
                try:
                    item["assertTarget"](item["target"])
                    if item["targetBytes"] is None:
                        item["target"].unlink(missing_ok=True)
                    else:
                        _atomic_write(
                            item["target"],
                            item["targetBytes"],
                            item["assertTarget"],
                        )
                except (DoctorError, OSError) as rollback_error:
                    rollback_errors.append(
                        f"{item['relative'].as_posix()}: {rollback_error}"
                    )
            report = _rollback_report(
                files=files,
                receipt=trusted_receipt,
                installation_kind=kind,
                changed=changed,
                error=error,
                rollback_errors=rollback_errors,
            )
            raise RepairFailed(report["note"], report) from error
        for file in files:
            if file["before"] != "current":
                file["state"] = "updated"
    elif not changed:
        installation_checks = _validate_installation(
            skill_root,
            hook_path,
            managed_markdown,
            assert_skill_target,
            assert_hook_target,
        )

    return {
        "status": "updated" if apply and changed else ("drift" if changed else "current"),
        "integrityState": "local_modification_detected" if changed else "healthy",
        "recoveryState": (
            "repaired"
            if apply and changed
            else ("trusted_repair_available" if changed else "not_needed")
        ),
        "installationKind": kind,
        "sourcePlugin": str(source_plugin.resolve(strict=True)),
        "skillRoot": str(canonical_skill_root),
        "hookPath": str(canonical_hook_path),
        "changedFiles": changed,
        "files": files,
        "installationChecks": installation_checks,
        "trustedReceipt": trusted_receipt,
        "repairScope": "declared managed files only",
        "note": "Unexpected installation files and all project state are preserved.",
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
        "--installation-kind",
        choices=sorted(INSTALLATION_KINDS),
        default="auto",
        help=(
            "Installation owner. Auto detects marketplace cache/plugin roots; "
            "marketplace targets are never repaired in place."
        ),
    )
    parser.add_argument(
        "--expected-package-version",
        help=(
            "Exact manual-package version from separately published release metadata; "
            "required with --expected-receipt-sha256 for non-marketplace packages."
        ),
    )
    parser.add_argument(
        "--expected-receipt-sha256",
        help=(
            "Exact release-receipt.json SHA-256 from separately published release metadata; "
            "required with --expected-package-version for non-marketplace packages."
        ),
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
            installation_kind=args.installation_kind,
            expected_receipt_sha256=args.expected_receipt_sha256,
            expected_package_version=args.expected_package_version,
        )
        if report.get("status") == "error":
            exit_code = 1
    except RepairFailed as error:
        report = error.report
        exit_code = 1
    except (DoctorError, OSError) as error:
        report = {
            "status": "error",
            "integrityState": "unknown",
            "recoveryState": "manual_action_required",
            "error": str(error),
        }
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
            "integrityState": report.get("integrityState", "unknown"),
            "recoveryState": report.get("recoveryState", "manual_action_required"),
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
    if report["status"] == "drift":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
