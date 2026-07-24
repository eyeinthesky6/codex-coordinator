# Optional Mission Control

Read this file only when the user asks to open or inspect Mission Control.

Mission Control is a manually started, read-only local page for one explicit enabled project. It is
not part of SessionStart, does not monitor in the background, sends no task messages, changes no
claims, and refreshes only when the user presses the page button.

From the installed plugin root, run:

```shell
python mission_control/mission_control.py --project-root <absolute-project-path>
```

The server binds only to `127.0.0.1`. Stop it with `Ctrl+C`. If the project is disabled, incompatible,
or unreadable, report the error; do not enable, migrate, repair, or alter that project merely to open
the page.
