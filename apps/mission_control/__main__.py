from . import _PLUGIN_ROOT  # noqa: F401
from mission_control.server import main


if __name__ == "__main__":
    raise SystemExit(main())
