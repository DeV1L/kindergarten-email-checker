"""HTTP endpoints for the Kubernetes probes (docs/ARCHITECTURE.md, "Deployment").

GET /readyz answers 200 after the start check of Telegram, Gmail and DeepSeek.
GET /livez answers 200 while the process runs.
The server runs in a daemon thread. The main loop does not depend on it.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ready = False  # set by the main loop after the start check


def status(path: str) -> int:
    """HTTP status code for a probe path."""
    if path == "/readyz":
        return 200 if ready else 503
    if path == "/livez":
        return 200
    return 404


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(status(self.path))
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass  # the probes call every few seconds; one line per call would fill the log


def start(port: int) -> HTTPServer:
    """Start the server in a daemon thread. Port 0 picks a free port, for tests."""
    server = HTTPServer(("", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
