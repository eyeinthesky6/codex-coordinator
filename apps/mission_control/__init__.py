"""Source-checkout compatibility package for bundled Mission Control."""

from __future__ import annotations

import sys
from pathlib import Path


_PLUGIN_ROOT = (
    Path(__file__).resolve().parents[2] / "plugins" / "codex-coordinator"
)
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))
