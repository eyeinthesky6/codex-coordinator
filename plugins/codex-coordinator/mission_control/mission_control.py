#!/usr/bin/env python3
"""Serve one project's active Coordinator board as a manual read-only dashboard."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import sys
import webbrowser
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_PORT = 8765


@lru_cache(maxsize=1)
def _state_module() -> Any:
    helper = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "codex-coordinator"
        / "scripts"
        / "coordination_state.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_codex_coordinator_state_for_mission_control", helper
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("The installed Coordinator state helper is unavailable")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def read_board(project_root: Path) -> dict[str, Any]:
    """Read only the enabled schema-2 active board through its canonical helper."""

    module = _state_module()
    return module.list_board(project_root)


def _items(values: object) -> str:
    if not isinstance(values, list) or not values:
        return '<span class="muted">None</span>'
    return "".join(f"<li>{html.escape(str(value))}</li>" for value in values)


def _cards(records: object) -> str:
    if not isinstance(records, list) or not records:
        return (
            '<div class="empty"><h2>No active coordinated tasks</h2>'
            "<p>Start or claim work in Codex, then refresh this page.</p></div>"
        )
    cards: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        cards.append(
            "".join(
                (
                    '<article class="card">',
                    '<div class="card-head">',
                    f"<h2>{html.escape(str(record.get('title', 'Untitled task')))}</h2>",
                    f"<span class=\"status\">{html.escape(str(record.get('status', 'active')))}</span>",
                    "</div>",
                    f"<p>{html.escape(str(record.get('goal', '')))}</p>",
                    '<div class="meta"><strong>Task</strong>',
                    f"<code>{html.escape(str(record.get('threadId', 'unknown')))}</code></div>",
                    '<div class="split"><section><h3>Working in</h3><ul>',
                    _items(record.get("paths")),
                    "</ul></section><section><h3>Exclusive actions</h3><ul>",
                    _items(record.get("actions")),
                    "</ul></section></div></article>",
                )
            )
        )
    return "".join(cards)


def _alerts(title: str, values: object, empty: str) -> str:
    rows: list[str] = []
    if isinstance(values, list):
        for value in values:
            if isinstance(value, dict):
                requested = html.escape(str(value.get("requestedBy", "unknown")))
                owner = html.escape(str(value.get("threadId", "unknown")))
                detail = html.escape(
                    str(value.get("action") or value.get("path") or "shared boundary")
                )
                rows.append(f"<li><code>{requested}</code> and <code>{owner}</code>: {detail}</li>")
    body = "".join(rows) if rows else f'<li class="muted">{html.escape(empty)}</li>'
    return f"<section class=\"alert-block\"><h2>{html.escape(title)}</h2><ul>{body}</ul></section>"


def render_dashboard(board: dict[str, Any], project_root: Path) -> bytes:
    project = html.escape(str(board.get("projectId", "unknown")))
    count = int(board.get("activeCount", 0))
    ceiling = html.escape(str(board.get("defaultLimit", "unknown")))
    root = html.escape(str(project_root))
    content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{project} · Mission Control</title>
<style>
:root{{--bg:#07111f;--panel:#0d1b2d;--line:#24405e;--text:#f5f8fc;--muted:#9eb0c5;--cyan:#69d7ff;--violet:#b998ff;--ok:#78e6ae}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top right,#172853 0,transparent 34%),var(--bg);color:var(--text);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1160px;margin:auto;padding:48px 24px 72px}}header{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:32px}}
h1{{font-size:clamp(2rem,5vw,4rem);line-height:1.02;margin:.15em 0}}h2{{font-size:1.15rem;margin:0}}h3{{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
p{{color:var(--muted)}}button{{border:1px solid var(--cyan);background:transparent;color:var(--text);padding:10px 16px;border-radius:999px;cursor:pointer}}
.eyebrow{{color:var(--cyan);font-weight:700}}.summary{{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0 36px}}.pill{{border:1px solid var(--line);background:#0a1728;padding:9px 13px;border-radius:999px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}.card,.alert-block,.empty{{background:linear-gradient(145deg,#10243a,#0a1727);border:1px solid var(--line);border-radius:18px;padding:20px}}
.card-head{{display:flex;justify-content:space-between;gap:16px}}.status{{color:var(--ok);font-size:.78rem;text-transform:uppercase}}.meta{{display:grid;gap:6px;margin:20px 0}}code{{overflow-wrap:anywhere;color:var(--violet)}}
.split{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}ul{{margin:0;padding-left:20px}}.alerts{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:24px}}.muted{{color:var(--muted)}}
footer{{margin-top:28px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:.9rem}}@media(max-width:680px){{header,.alerts{{display:block}}button{{margin-top:16px}}.alert-block{{margin-top:16px}}}}
</style></head><body><main>
<header><div><div class="eyebrow">Codex Coordinator</div><h1>Mission Control</h1><p>See who is working on what without opening every task.</p></div><button type="button" onclick="location.reload()">Refresh board</button></header>
<div class="summary"><span class="pill"><strong>{count}</strong> active tasks</span><span class="pill">Normal ceiling <strong>{ceiling}</strong></span><span class="pill">Project <strong>{project}</strong></span></div>
<section class="grid">{_cards(board.get('records'))}</section>
<section class="alerts">{_alerts('Exact conflicts', board.get('conflicts'), 'No exact exclusive-action conflicts.')}{_alerts('Shared-path warnings', board.get('warnings'), 'No shared-path warnings.')}</section>
<footer>Read-only local view of <code>{root}</code>. It sends no messages, controls no tasks, stores no transcripts, and refreshes only when you ask.</footer>
</main></body></html>"""
    return content.encode("utf-8")


def _handler(project_root: Path) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - HTTP handler contract
            if self.path.split("?", 1)[0] != "/":
                self.send_error(404)
                return
            try:
                payload = render_dashboard(read_board(project_root), project_root)
            except (OSError, RuntimeError, ValueError) as exc:
                payload = (
                    "<!doctype html><meta charset=utf-8><title>Mission Control unavailable</title>"
                    f"<h1>Mission Control could not read this project</h1><p>{html.escape(str(exc))}</p>"
                ).encode("utf-8")
                self.send_response(503)
            else:
                self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return DashboardHandler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open one project's Coordinator board in a manual read-only dashboard."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = args.project_root.resolve(strict=True)
    if not project_root.is_dir():
        raise SystemExit("project-root must be a local directory")
    if not 0 <= args.port <= 65535:
        raise SystemExit("port must be between 0 and 65535")
    try:
        read_board(project_root)
    except (OSError, RuntimeError, ValueError) as exc:
        json.dump({"status": "unavailable", "error": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 1
    server = ThreadingHTTPServer(("127.0.0.1", args.port), _handler(project_root))
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    json.dump({"status": "ready", "url": url, "projectRoot": str(project_root)}, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
