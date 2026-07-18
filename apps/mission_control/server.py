from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .collector import (
    Collector,
    DeepReviewRunner,
    DoctorRunner,
    SettingsStore,
    default_data_dir,
)


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
REPO_ROOT = APP_DIR.parent.parent
LOGO_PATH = REPO_ROOT / "plugins" / "codex-coordinator" / "assets" / "logo.png"
DOCTOR_CONTRACT_VERSION = 2


class MissionControlRuntime:
    def __init__(self, roots: list[Path], codex_home: Path | None, data_dir: Path):
        self.settings = SettingsStore(data_dir)
        self.collector = Collector(roots, codex_home=codex_home)
        self.doctor = DoctorRunner(data_dir, REPO_ROOT, self.collector.codex_home)
        self.deep_review = DeepReviewRunner(
            data_dir, REPO_ROOT, self.collector.codex_home
        )
        self._lock = threading.RLock()
        self._scan_lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._snapshot: dict[str, Any] = {}
        self._doctor_running = False
        self._deep_review_running = False
        self._thread: threading.Thread | None = None

    def _decorate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings.get()
        snapshot["settings"] = settings.public_dict()
        doctor = self.doctor.read_state()
        doctor["running"] = self._doctor_running or doctor["running"]
        deep_review = self.deep_review.read_state()
        deep_review["running"] = self._deep_review_running or deep_review["running"]
        doctor["deepReview"] = deep_review
        snapshot["doctor"] = doctor
        return snapshot

    def scan(self) -> dict[str, Any]:
        with self._scan_lock:
            snapshot = self.collector.collect()
            with self._lock:
                self._snapshot = self._decorate(snapshot)
            return self.get_snapshot()

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._snapshot))

    def update_settings(self, changes: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings.update(changes)
        with self._lock:
            if self._snapshot:
                self._snapshot = self._decorate(self._snapshot)
        self._wake.set()
        return settings.public_dict()

    def start_doctor(self) -> dict[str, Any]:
        with self._lock:
            if self._doctor_running or self._deep_review_running:
                return self.get_snapshot()
            self._doctor_running = True
            frozen_snapshot = json.loads(json.dumps(self._snapshot))
            if self._snapshot:
                self._snapshot = self._decorate(self._snapshot)

        def run() -> None:
            try:
                self.doctor.run(frozen_snapshot)
            finally:
                with self._lock:
                    self._doctor_running = False
                    if self._snapshot:
                        self._snapshot = self._decorate(self._snapshot)
                self.scan()

        threading.Thread(target=run, name="mission-control-doctor", daemon=True).start()
        return self.get_snapshot()

    def start_deep_review(self) -> dict[str, Any]:
        with self._lock:
            if self._doctor_running or self._deep_review_running:
                return self.get_snapshot()
            self._deep_review_running = True
            frozen_snapshot = json.loads(json.dumps(self._snapshot))
            if self._snapshot:
                self._snapshot = self._decorate(self._snapshot)

        def run() -> None:
            try:
                self.deep_review.run(frozen_snapshot)
            finally:
                with self._lock:
                    self._deep_review_running = False
                    if self._snapshot:
                        self._snapshot = self._decorate(self._snapshot)
                self.scan()

        threading.Thread(
            target=run, name="mission-control-deep-review", daemon=True
        ).start()
        return self.get_snapshot()

    def start(self) -> None:
        self.doctor.recover_interrupted_run()
        self.deep_review.recover_interrupted_run()
        self.scan()

        def loop() -> None:
            while not self._stop.is_set():
                delay = self.settings.get().refresh_seconds
                self._wake.clear()
                if self._wake.wait(delay):
                    continue
                if self._stop.is_set():
                    break
                self.scan()

        self._thread = threading.Thread(target=loop, name="mission-control-collector", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=2)


class MissionControlHandler(BaseHTTPRequestHandler):
    server_version = "CodexMissionControl/0.1"

    @property
    def runtime(self) -> MissionControlRuntime:
        return self.server.runtime  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        )

    def _request_host(self) -> tuple[str, int | None] | None:
        host = self.headers.get("Host", "").strip()
        if not host:
            return None
        try:
            parsed = urlsplit("//" + host)
            hostname = (parsed.hostname or "").lower()
            port = parsed.port
        except ValueError:
            return None
        if hostname not in {"127.0.0.1", "localhost", "::1"}:
            return None
        return hostname, port

    def _allow_local_request(self, *, write: bool = False) -> bool:
        request_host = self._request_host()
        if request_host is None:
            self._send_json({"error": "Mission Control accepts localhost requests only."}, HTTPStatus.FORBIDDEN)
            return False
        if not write:
            return True
        origin = self.headers.get("Origin", "").strip()
        if origin:
            try:
                parsed = urlsplit(origin)
                origin_host = ((parsed.hostname or "").lower(), parsed.port)
            except ValueError:
                origin_host = ("", None)
                parsed = urlsplit("")
            if parsed.scheme != "http" or origin_host != request_host:
                self._send_json({"error": "Cross-site requests are not allowed."}, HTTPStatus.FORBIDDEN)
                return False
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._send_json({"error": "Expected application/json."}, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return False
        return True

    def _send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        mime = (
            "text/plain"
            if path.suffix.lower() == ".mmd"
            else mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        )
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if not self._allow_local_request():
            return
        path = urlsplit(self.path).path
        if path == "/api/snapshot":
            self._send_json(self.runtime.get_snapshot())
            return
        if path == "/api/settings":
            self._send_json(self.runtime.settings.get().public_dict())
            return
        if path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "scope": "localhost",
                    "doctorContractVersion": DOCTOR_CONTRACT_VERSION,
                }
            )
            return
        if path in {"/", "/index.html"}:
            self._send_file(STATIC_DIR / "index.html")
            return
        if path == "/logo.png":
            self._send_file(LOGO_PATH)
            return
        static_files = {
            "/styles.css": STATIC_DIR / "styles.css",
            "/app.js": STATIC_DIR / "app.js",
        }
        if path in static_files:
            self._send_file(static_files[path])
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid request size") from error
        if length < 0 or length > 64 * 1024:
            raise ValueError("Request is too large")
        try:
            value = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as error:
            raise ValueError("Invalid JSON") from error
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object")
        return value

    def do_POST(self) -> None:
        if not self._allow_local_request(write=True):
            return
        path = urlsplit(self.path).path
        try:
            if path == "/api/settings":
                self._send_json(self.runtime.update_settings(self._read_json()))
                return
            if path == "/api/refresh":
                self._read_json()
                self._send_json(self.runtime.scan())
                return
            if path == "/api/doctor":
                self._read_json()
                self._send_json(self.runtime.start_doctor(), HTTPStatus.ACCEPTED)
                return
            if path == "/api/doctor/deep-review":
                request = self._read_json()
                if request.get("confirmation") != "user-triggered-model-review":
                    raise ValueError("Deep Review requires an explicit user-triggered confirmation.")
                self._send_json(
                    self.runtime.start_deep_review(), HTTPStatus.ACCEPTED
                )
                return
        except ValueError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)


class MissionControlServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], runtime: MissionControlRuntime):
        super().__init__(address, MissionControlHandler)
        self.runtime = runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Codex Mission Control dashboard.")
    parser.add_argument(
        "--project",
        action="append",
        dest="projects",
        type=Path,
        help="Coordinator-enabled project to watch. Repeat for more projects. Defaults to the current directory.",
    )
    parser.add_argument("--port", type=int, default=4317, help="Local port (default: 4317).")
    parser.add_argument("--no-open", action="store_true", help="Do not open the dashboard in the default browser.")
    parser.add_argument("--codex-home", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--data-dir", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.port <= 65535:
        raise SystemExit("Port must be between 1 and 65535.")
    roots = args.projects or [Path.cwd()]
    runtime = MissionControlRuntime(roots, args.codex_home, args.data_dir or default_data_dir())
    server = MissionControlServer(("127.0.0.1", args.port), runtime)
    runtime.start()
    url = f"http://127.0.0.1:{args.port}"
    print(f"Mission Control is live at {url}")
    print("Local only. Press Ctrl+C to stop.")
    if not args.no_open:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.stop()
    return 0
