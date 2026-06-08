"""Async↔Qt bridge for the viewer.

NetworkWorker runs an asyncio event loop inside a QThread.
The GUI sends commands via thread-safe calls; the worker emits Qt signals
back to the main thread to update the UI.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.auth import TokenAuthenticator, UserAccountAuthenticator
from ..core.config import Config
from ..core.feature import FeatureHandler, FeatureRegistry
from ..core.protocol import BinaryFrame, BinaryMessageType, Message, MessageType
from ..core.session import Monitor, Session
from ..viewer.client import ViewerClient
from ..viewer.features.clipboard import ClipboardFeature
from ..viewer.features.files import FileTransferFeature

if TYPE_CHECKING:
    from ..core.transport import Connection

log = logging.getLogger(__name__)


class NetworkWorker(QThread):
    # ── Signals ──────────────────────────────────────────────────────────
    frame_received      = pyqtSignal(bytes)
    connected           = pyqtSignal(str)           # host:port
    disconnected        = pyqtSignal(str)           # reason / empty string
    monitor_list_changed = pyqtSignal(list)         # list[dict]
    clipboard_received  = pyqtSignal(str)
    status_changed      = pyqtSignal(str)
    fps_updated         = pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cfg: Config | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._input_queue: asyncio.Queue | None = None
        self._stop_event: asyncio.Event | None = None
        self._clipboard_feature: ClipboardFeature | None = None

    # ── Public API (called from Qt main thread) ───────────────────────────

    def configure(self, cfg: Config) -> None:
        self._cfg = cfg

    def start_connection(self) -> None:
        loop = self._loop
        if loop and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._restart(), loop)

    def stop_connection(self) -> None:
        loop = self._loop
        stop = self._stop_event
        if loop and not loop.is_closed() and stop:
            try:
                loop.call_soon_threadsafe(stop.set)
            except RuntimeError:
                pass

    def send_input(self, event: dict) -> None:
        loop = self._loop
        queue = self._input_queue
        if loop and not loop.is_closed() and queue:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:
                pass

    def push_clipboard(self) -> None:
        loop = self._loop
        if loop and not loop.is_closed() and self._clipboard_feature:
            asyncio.run_coroutine_threadsafe(self._do_push_clipboard(), loop)

    def pull_clipboard(self) -> None:
        loop = self._loop
        if loop and not loop.is_closed() and self._clipboard_feature:
            asyncio.run_coroutine_threadsafe(self._do_pull_clipboard(), loop)

    # ── QThread entry ─────────────────────────────────────────────────────

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._input_queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
        try:
            self._loop.run_until_complete(self._run_client())
        finally:
            self._loop.close()
            self._loop = None
            self._input_queue = None
            self._stop_event = None
            self._clipboard_feature = None

    # ── Internal async methods ────────────────────────────────────────────

    async def _restart(self) -> None:
        self._stop_event.set()
        await asyncio.sleep(0.1)
        self._stop_event.clear()
        asyncio.create_task(self._run_client())

    async def _run_client(self) -> None:
        if not self._cfg:
            return

        display    = _GUIDisplayFeature(self)
        input_feat = _GUIInputFeature(self._input_queue)
        clipboard  = ClipboardFeature()
        self._clipboard_feature = clipboard
        files      = FileTransferFeature(self._cfg)

        # Wire clipboard signal
        original_handle = clipboard.handle
        async def _clipboard_handle(session, transport, msg):
            await original_handle(session, transport, msg)
            if isinstance(msg, Message) and msg.type == MessageType.CLIPBOARD_DATA:
                self.clipboard_received.emit(msg.payload.get("content", ""))
        clipboard.handle = _clipboard_handle

        registry = FeatureRegistry()
        registry.register(display)
        registry.register(input_feat)
        registry.register(clipboard)
        registry.register(files)

        auth = self._build_auth()
        client = ViewerClient(self._cfg, registry, auth)

        host = self._cfg.server.host
        port = self._cfg.server.port

        # Patch ViewerClient to emit signals on connect/disconnect
        original_connect_once = client._connect_once
        async def _patched_connect_once(attempt):
            try:
                self.connected.emit(f"{host}:{port}")
            except RuntimeError:
                return
            try:
                await original_connect_once(attempt)
            finally:
                try:
                    self.disconnected.emit("")
                except RuntimeError:
                    pass
        client._connect_once = _patched_connect_once

        # Run until stop_event is set or client exits
        client_task = asyncio.create_task(client.run())
        stop_task   = asyncio.create_task(self._stop_event.wait())
        done, pending = await asyncio.wait(
            [client_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def _do_push_clipboard(self) -> None:
        pass  # handled by _GUIInputFeature forwarding to ClipboardFeature

    async def _do_pull_clipboard(self) -> None:
        pass

    def _build_auth(self):
        cfg = self._cfg.auth
        if cfg.mode == "users":
            from ..accounts.store import UserStore
            store = UserStore("data/users.json")
            return UserAccountAuthenticator(store, cfg.username, cfg.password)
        return TokenAuthenticator(cfg.token)


# ── Feature implementations that emit Qt signals ──────────────────────────

class _GUIDisplayFeature(FeatureHandler):
    handles       = frozenset({MessageType.MONITOR_LIST, MessageType.DISPLAY_STATUS})
    handles_binary = True

    def __init__(self, worker: NetworkWorker) -> None:
        self._worker = worker
        self._frame_count = 0
        self._fps_task: asyncio.Task | None = None

    async def on_connect(self, session: Session, transport: "Connection") -> None:
        self._frame_count = 0
        self._fps_task = asyncio.create_task(self._fps_loop())

    async def on_disconnect(self, session: Session) -> None:
        if self._fps_task:
            self._fps_task.cancel()

    async def handle(self, session: Session, transport: "Connection", msg) -> None:
        if isinstance(msg, BinaryFrame):
            if msg.type == BinaryMessageType.FRAME:
                self._worker.frame_received.emit(msg.data)
                self._frame_count += 1
            return

        if msg.type == MessageType.MONITOR_LIST:
            monitors = msg.payload.get("monitors", [])
            session.monitors = [Monitor.from_dict(m) for m in monitors]
            self._worker.monitor_list_changed.emit(monitors)

        elif msg.type == MessageType.DISPLAY_STATUS:
            self._worker.status_changed.emit(msg.payload.get("text", ""))

    async def _fps_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(1.0)
                try:
                    self._worker.fps_updated.emit(float(self._frame_count))
                except RuntimeError:
                    return
                self._frame_count = 0
        except asyncio.CancelledError:
            pass


class _GUIInputFeature(FeatureHandler):
    """Drains the input queue and sends events to the agent."""
    handles = frozenset()

    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue
        self._transport: "Connection | None" = None
        self._task: asyncio.Task | None = None

    async def on_connect(self, session: Session, transport: "Connection") -> None:
        self._transport = transport
        self._task = asyncio.create_task(self._drain(), name="gui_input_drain")

    async def on_disconnect(self, session: Session) -> None:
        if self._task:
            self._task.cancel()
        self._transport = None

    async def _drain(self) -> None:
        try:
            while True:
                event = await self._queue.get()
                if self._transport is None:
                    continue
                msg_type_val = event.pop("type")
                msg_type = MessageType(msg_type_val) if isinstance(msg_type_val, str) else msg_type_val
                await self._transport.send_message(Message(msg_type, event))
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("GUI input drain error")
