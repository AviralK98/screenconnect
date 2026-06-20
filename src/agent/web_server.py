"""Lightweight HTTP server that serves the mobile web viewer page.

The page itself (``src/web/viewer.html``) is a self-contained HTML/JS
viewer. A phone browses to ``http://<agent-ip>:<web_port>/`` and the page
connects back to the agent's WebSocket server to view and control the screen.

This runs in its own daemon thread, independent of the asyncio WebSocket
server, so it can be toggled on/off from the GUI without touching the
control plane.
"""
from __future__ import annotations

import http.server
import logging
import socket
import sys
import threading
from pathlib import Path

log = logging.getLogger(__name__)


def _html_path() -> Path:
    """Locate viewer.html in both source runs and PyInstaller bundles."""
    if getattr(sys, "frozen", False):
        # PyInstaller unpacks bundled data under sys._MEIPASS
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))
        return base / "src" / "web" / "viewer.html"
    return Path(__file__).parent.parent / "web" / "viewer.html"


_HTML_PATH = _html_path()


def local_ip() -> str:
    """Best-effort LAN IP address for display in the UI."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))   # no packets sent; just picks the route
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class _ViewerHandler(http.server.BaseHTTPRequestHandler):
    # Overridden per-instance subclass in WebViewerServer.start()
    ws_port: int = 8765
    ws_scheme: str = "ws"

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        path = self.path.split("?", 1)[0]
        if path not in ("/", "/index.html", "/viewer.html"):
            self.send_error(404, "Not found")
            return
        try:
            html = _HTML_PATH.read_text(encoding="utf-8")
        except OSError:
            self.send_error(500, "viewer.html not found on agent")
            return
        html = (html
                .replace("__WS_PORT__", str(self.ws_port))
                .replace("__WS_SCHEME__", self.ws_scheme))
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # quiet by default
        log.debug("web-viewer: " + fmt, *args)


class WebViewerServer:
    """Serves the mobile viewer page on a background thread."""

    def __init__(self, host: str, http_port: int, ws_port: int,
                 ws_scheme: str = "ws") -> None:
        self._host = host
        self._http_port = http_port
        self._ws_port = ws_port
        self._ws_scheme = ws_scheme
        self._server: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    def start(self) -> None:
        if self._server is not None:
            return
        handler = type(
            "BoundViewerHandler", (_ViewerHandler,),
            {"ws_port": self._ws_port, "ws_scheme": self._ws_scheme},
        )
        self._server = http.server.ThreadingHTTPServer((self._host, self._http_port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="web-viewer", daemon=True,
        )
        self._thread.start()
        log.info("Mobile web viewer serving on http://%s:%d", local_ip(), self._http_port)

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
        log.info("Mobile web viewer stopped")
