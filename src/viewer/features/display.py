from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import cv2
import numpy as np

from ...core.feature import FeatureHandler
from ...core.protocol import BinaryFrame, BinaryMessageType, Message, MessageType
from ...core.session import Monitor

if TYPE_CHECKING:
    from ...core.session import Session
    from ...core.transport import Connection

log = logging.getLogger(__name__)

WINDOW = "ScreenConnect"
STATUS_DURATION = 2.0   # seconds to show overlay text


class DisplayFeature(FeatureHandler):
    handles = frozenset({MessageType.MONITOR_LIST, MessageType.DISPLAY_STATUS})
    handles_binary = True

    def __init__(self) -> None:
        self._status_text: str = ""
        self._status_until: float = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._event_queue: asyncio.Queue | None = None

    def set_event_queue(self, queue: asyncio.Queue) -> None:
        self._event_queue = queue

    async def on_connect(self, session: "Session", transport: "Connection") -> None:
        self._loop = asyncio.get_running_loop()
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        self._set_status("Connected", duration=STATUS_DURATION)

    async def on_disconnect(self, session: "Session") -> None:
        pass

    async def handle(self, session: "Session", transport: "Connection", msg) -> None:
        if isinstance(msg, BinaryFrame):
            if msg.type == BinaryMessageType.FRAME:
                self._render_frame(msg.data)
            return

        if msg.type == MessageType.MONITOR_LIST:
            monitors = [Monitor.from_dict(m) for m in msg.payload.get("monitors", [])]
            session.monitors = monitors
            names = "  ".join(f"[M{m.id}:{m.name}]" for m in monitors)
            self._set_status(f"Monitors: {names}  |  Ctrl+M to cycle", duration=4.0)

        elif msg.type == MessageType.DISPLAY_STATUS:
            self._set_status(msg.payload.get("text", ""), duration=3.0)

    def _render_frame(self, jpeg: bytes) -> None:
        data = np.frombuffer(jpeg, dtype=np.uint8)
        frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if frame is None:
            return

        if self._status_text and time.monotonic() < self._status_until:
            self._overlay_text(frame, self._status_text)
        elif self._status_text:
            self._status_text = ""

        cv2.imshow(WINDOW, frame)

    def _overlay_text(self, frame: np.ndarray, text: str) -> None:
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale, thickness = 0.7, 2
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        x, y = 10, h - 10
        cv2.rectangle(frame, (x - 4, y - th - 8), (x + tw + 4, y + 4), (0, 0, 0), -1)
        cv2.putText(frame, text, (x, y), font, scale, (255, 255, 255), thickness)

    def _set_status(self, text: str, duration: float = 2.0) -> None:
        self._status_text = text
        self._status_until = time.monotonic() + duration

    def poll_window_events(self) -> int:
        """Call from the main thread; returns last cv2.waitKey value."""
        key = cv2.waitKey(1) & 0xFF
        return key

    def destroy(self) -> None:
        cv2.destroyAllWindows()
