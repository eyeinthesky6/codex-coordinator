#!/usr/bin/env python3
"""Start, stop, and inspect the bundled local Mission Control server."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from mission_control.lifecycle import lifecycle_lock, read_state, write_state


DEFAULT_PORT = 4317
HEALTH_TIMEOUT_SECONDS = 0.35


def _data_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "CodexCoordinator" / "MissionControl"
    return Path.home() / ".local" / "share" / "codex-coordinator" / "mission-control"


def _lifecycle_path() -> Path:
    return _data_dir() / "lifecycle.json"


def _read_lifecycle() -> dict[str, Any]:
    return read_state(_lifecycle_path())


def _write_lifecycle(*, enabled: bool, browser_opened: bool | None = None) -> None:
    write_state(
        _lifecycle_path(), enabled=enabled, browser_opened=browser_opened
    )


def _url(port: int, path: str = "") -> str:
    return f"http://127.0.0.1:{port}{path}"


def _health(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            _url(port, "/api/health"), timeout=HEALTH_TIMEOUT_SECONDS
        ) as response:
            value = json.load(response)
        return response.status == 200 and value.get("scope") == "localhost"
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _shutdown(port: int) -> bool:
    request = urllib.request.Request(
        _url(port, "/api/shutdown"),
        data=json.dumps({"confirmation": "user-requested-shutdown"}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 202
    except (OSError, urllib.error.URLError):
        return False


def _module_command() -> tuple[Path, str]:
    plugin_root = Path(__file__).resolve().parent.parent
    if (plugin_root / "mission_control" / "__main__.py").is_file():
        return plugin_root, "mission_control"
    source_root = plugin_root.parent.parent
    if (source_root / "apps" / "mission_control" / "__main__.py").is_file():
        return source_root, "apps.mission_control"
    raise FileNotFoundError("The Mission Control runtime is not included in this installation.")


def _spawn(project: Path, port: int, *, open_browser: bool) -> None:
    working_directory, module = _module_command()
    command = [
        sys.executable,
        "-m",
        module,
        "--project",
        str(project.resolve(strict=False)),
        "--port",
        str(port),
    ]
    if not open_browser:
        command.append("--no-open")
    options: dict[str, Any] = {
        "cwd": str(working_directory),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        options["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    else:
        options["start_new_session"] = True
    subprocess.Popen(command, **options)


def start(project: Path, port: int, *, automatic: bool, open_browser: bool) -> str:
    with lifecycle_lock(_lifecycle_path()):
        return _start_locked(project, port, automatic=automatic, open_browser=open_browser)


def _start_locked(
    project: Path, port: int, *, automatic: bool, open_browser: bool
) -> str:
    state = _read_lifecycle()
    enabled = state.get("automatic_start_enabled", True)
    if automatic and enabled is False:
        return "disabled"
    if not automatic:
        enabled = True
        _write_lifecycle(enabled=True)

    if _health(port):
        if open_browser:
            import webbrowser

            webbrowser.open(_url(port))
        return "running"

    first_open = automatic and not bool(state.get("browser_opened"))
    should_open = open_browser or first_open
    _spawn(project, port, open_browser=should_open)
    _write_lifecycle(enabled=bool(enabled), browser_opened=bool(state.get("browser_opened")) or should_open)
    for _ in range(50):
        if _health(port):
            return "started"
        time.sleep(0.05)
    return "starting"


def stop(port: int) -> str:
    with lifecycle_lock(_lifecycle_path()):
        state = _read_lifecycle()
        _write_lifecycle(
            enabled=False, browser_opened=bool(state.get("browser_opened"))
        )
    if not _shutdown(port):
        return "not-running"
    for _ in range(20):
        if not _health(port):
            return "stopped"
        time.sleep(0.05)
    return "stopping"


def status(port: int) -> dict[str, Any]:
    state = _read_lifecycle()
    return {
        "running": _health(port),
        "automatic_start_enabled": state.get("automatic_start_enabled", True),
        "url": _url(port),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control the local Mission Control server.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Enable and start Mission Control.")
    start_parser.add_argument("--project", type=Path, default=Path.cwd())
    start_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    start_parser.add_argument("--open", action="store_true", dest="open_browser")
    start_parser.add_argument("--automatic", action="store_true", help=argparse.SUPPRESS)

    stop_parser = subparsers.add_parser("stop", help="Disable and stop Mission Control.")
    stop_parser.add_argument("--port", type=int, default=DEFAULT_PORT)

    status_parser = subparsers.add_parser("status", help="Show Mission Control status.")
    status_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.port <= 65535:
        raise SystemExit("Port must be between 1 and 65535.")
    try:
        if args.command == "start":
            result = start(
                args.project,
                args.port,
                automatic=args.automatic,
                open_browser=args.open_browser,
            )
            print(json.dumps({"status": result, **status(args.port)}))
        elif args.command == "stop":
            result = stop(args.port)
            print(json.dumps({"status": result, **status(args.port)}))
        else:
            print(json.dumps(status(args.port)))
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
