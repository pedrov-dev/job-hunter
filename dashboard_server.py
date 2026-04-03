"""
dashboard_server.py
-------------------
Local HTTP server for the JobBot dashboard.
Serves the HTML UI and exposes small JSON endpoints for the live feed,
status updates, and triggering a new pipeline run.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from config import BASE_DIR
from tracking.tracker import build_dashboard_feed, init_db, update_status

log = logging.getLogger("jobbot.dashboard")
ALLOWED_STATUSES = {"applied", "interviewing", "offer", "rejected", "error"}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class PipelineRunState:
    process: subprocess.Popen[str] | None = None
    last_started_at: str | None = None
    last_finished_at: str | None = None
    last_returncode: int | None = None
    last_output: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def as_dict(self) -> dict:
        proc = self.process
        running = proc is not None and proc.poll() is None
        return {
            "running": running,
            "last_started_at": self.last_started_at,
            "last_finished_at": self.last_finished_at,
            "last_returncode": self.last_returncode,
            "last_output": self.last_output,
        }


RUN_STATE = PipelineRunState()


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _watch_process(process: subprocess.Popen[str]) -> None:
    lines: list[str] = []
    if process.stdout is not None:
        for line in process.stdout:
            lines.append(line.rstrip())
            if len(lines) > 250:
                lines = lines[-250:]

    returncode = process.wait()
    with RUN_STATE.lock:
        if RUN_STATE.process is process:
            RUN_STATE.last_finished_at = _utc_now_iso()
            RUN_STATE.last_returncode = returncode
            RUN_STATE.last_output = "\n".join(lines).strip()
            RUN_STATE.process = None


def start_pipeline_run(
    *,
    dry_run: bool = False,
    limit: int | None = None,
    sweep_tier: str | None = None,
) -> tuple[bool, dict]:
    with RUN_STATE.lock:
        if RUN_STATE.process is not None and RUN_STATE.process.poll() is None:
            return False, RUN_STATE.as_dict()

        cmd = [sys.executable, str(BASE_DIR / "main.py")]
        if dry_run:
            cmd.append("--dry-run")
        if limit is not None:
            cmd.extend(["--limit", str(limit)])
        if sweep_tier:
            cmd.extend(["--sweep-tier", sweep_tier])

        log.info("Starting JobBot run: %s", " ".join(cmd))
        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        RUN_STATE.process = process
        RUN_STATE.last_started_at = _utc_now_iso()
        RUN_STATE.last_finished_at = None
        RUN_STATE.last_returncode = None
        RUN_STATE.last_output = ""

    threading.Thread(target=_watch_process, args=(process,), daemon=True).start()
    return True, RUN_STATE.as_dict()


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        log.info("dashboard %s", format % args)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8") or "{}")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/dashboard", "/dashboard/"}:
            self.path = "/ui/dashboard.html"
            return super().do_GET()

        if path == "/api/feed":
            init_db()
            payload = build_dashboard_feed()
            payload.update({"ok": True, "run_status": RUN_STATE.as_dict()})
            return self._send_json(payload)

        if path == "/api/run-status":
            return self._send_json({"ok": True, **RUN_STATE.as_dict()})

        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/run":
            payload = self._read_json_body()
            started, run_status = start_pipeline_run(
                dry_run=bool(payload.get("dry_run", False)),
                limit=_coerce_int(payload.get("limit")),
                sweep_tier=payload.get("sweep_tier") or None,
            )
            status = HTTPStatus.ACCEPTED if started else HTTPStatus.CONFLICT
            message = (
                "JobBot run started"
                if started
                else "A JobBot run is already in progress"
            )
            return self._send_json(
                {"ok": started, "message": message, "run_status": run_status},
                status=status,
            )

        if path == "/api/status":
            payload = self._read_json_body()
            job_id = str(payload.get("job_id", "")).strip()
            status = str(payload.get("status", "")).strip().lower()
            notes = str(payload.get("notes", "")).strip()

            if not job_id or status not in ALLOWED_STATUSES:
                return self._send_json(
                    {
                        "ok": False,
                        "error": "A valid job_id and status are required.",
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )

            init_db()
            update_status(job_id, status, notes=notes)
            feed = build_dashboard_feed()
            feed.update({"ok": True, "run_status": RUN_STATE.as_dict()})
            return self._send_json(feed)

        self._send_json(
            {"ok": False, "error": "Not found"},
            status=HTTPStatus.NOT_FOUND,
        )


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def run_dashboard_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser_on_start: bool = True,
) -> None:
    init_db()
    url = f"http://{host}:{port}/"

    with ReusableThreadingHTTPServer((host, port), DashboardRequestHandler) as server:
        log.info("Dashboard available at %s", url)
        print(f"Dashboard available at {url}")
        if open_browser_on_start:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("Dashboard server stopped")
