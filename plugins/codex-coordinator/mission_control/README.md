# Mission Control

Mission Control is an optional, manually started, read-only view of one enabled project's active
Coordinator board. It shows current task lanes, exact exclusive-action conflicts, and shared-path
warnings without opening every task.

It does not start with Codex, poll in the background, send task messages, create or stop tasks,
inspect transcripts, read private Codex databases, repair files, or change board state. The page
refreshes only when you press **Refresh board**.

From the installed plugin directory:

```powershell
python mission_control/mission_control.py --project-root C:\Projects\your-project
```

Press `Ctrl+C` in that terminal to stop the local server.
