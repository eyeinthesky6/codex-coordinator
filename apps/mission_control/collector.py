"""Compatibility import for the Mission Control runtime bundled in the plugin."""

from __future__ import annotations

from . import _PLUGIN_ROOT  # noqa: F401
from mission_control import collector as _implementation

globals().update(
    {
        name: getattr(_implementation, name)
        for name in dir(_implementation)
        if not name.startswith("__")
    }
)
