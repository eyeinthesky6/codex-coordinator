"""Compatibility entry point for the Doctor scanner bundled in the plugin."""

from __future__ import annotations

from . import _PLUGIN_ROOT  # noqa: F401
from mission_control import doctor_scan as _implementation

globals().update(
    {
        name: getattr(_implementation, name)
        for name in dir(_implementation)
        if not name.startswith("__")
    }
)


if __name__ == "__main__":
    raise SystemExit(_implementation.main())
