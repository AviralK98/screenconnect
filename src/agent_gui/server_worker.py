"""QThread that owns the asyncio event loop and runs AgentServer."""
from __future__ import annotations

import asyncio
import logging

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.auth import TokenAuthenticator, UserAccountAuthenticator
from ..core.config import Config
from ..core.feature import FeatureRegistry
from ..agent.server import AgentServer
from ..agent.features.screen import ScreenCaptureFeature
from ..agent.features.input import InputFeature
from ..agent.features.clipboard import ClipboardFeature
from ..agent.features.files import FileTransferFeature

log = logging.getLogger(__name__)


class ServerWorker(QThread):
    # ── Signals ───────────────────────────────────────────────────────────
    server_started    = pyqtSignal(str)   # "host:port"
    server_stopped    = pyqtSignal()
    client_connected  = pyqtSignal(str, str)   # address, user_label
    client_disconnected = pyqtSignal(str)       # address
    error_occurred    = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cfg: Config | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None

    def configure(self, cfg: Config) -> None:
        self._cfg = cfg

    def stop_server(self) -> None:
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        try:
            self._loop.run_until_complete(self._run_server())
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self._loop.close()
            self.server_stopped.emit()

    async def _run_server(self) -> None:
        cfg = self._cfg
        registry = FeatureRegistry()
        registry.register(ScreenCaptureFeature(cfg))
        registry.register(InputFeature())
        registry.register(ClipboardFeature())
        registry.register(FileTransferFeature(cfg))

        auth = self._build_auth()

        server = AgentServer(
            cfg,
            registry,
            auth,
            on_client_connect=self._on_connect,
            on_client_disconnect=self._on_disconnect,
        )

        host = cfg.server.host
        port = cfg.server.port

        # Run server until stop_event is set
        import websockets
        ssl_ctx = server._build_ssl()
        scheme = "wss" if cfg.tls.enabled else "ws"
        log.info("Agent listening on %s://%s:%d", scheme, host, port)

        async with websockets.serve(
            server._handle_connection,
            host,
            port,
            ssl=ssl_ctx,
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
        ):
            self.server_started.emit(f"{host}:{port}")
            await self._stop_event.wait()

        log.info("Server stopped")

    def _on_connect(self, address: str, user_label: str) -> None:
        self.client_connected.emit(address, user_label)

    def _on_disconnect(self, address: str) -> None:
        self.client_disconnected.emit(address)

    def _build_auth(self):
        cfg = self._cfg.auth
        if cfg.mode == "users":
            from ..accounts.store import UserStore
            store = UserStore("data/users.json")
            return UserAccountAuthenticator(store)
        return TokenAuthenticator(cfg.token)
