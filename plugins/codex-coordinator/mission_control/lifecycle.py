"""Small cross-process state helpers for Mission Control lifecycle ownership."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def read_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_state(
    path: Path, *, enabled: bool, browser_opened: bool | None = None
) -> None:
    state = read_state(path)
    state["automatic_start_enabled"] = enabled
    if browser_opened is not None:
        state["browser_opened"] = browser_opened
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)


@contextmanager
def lifecycle_lock(state_path: Path) -> Iterator[None]:
    lock_path = state_path.with_name("lifecycle.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor: int | None = None
    for _ in range(50):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode("ascii"))
            break
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > 30
            except OSError:
                stale = False
            if stale:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
            time.sleep(0.04)
    if descriptor is None:
        raise RuntimeError("Mission Control lifecycle is busy; try again.")
    try:
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except OSError:
            pass
