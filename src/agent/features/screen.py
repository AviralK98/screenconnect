from __future__ import annotations

import asyncio
import logging
import time
from io import BytesIO
from typing import TYPE_CHECKING

import mss
from PIL import Image

from ...core.feature import FeatureHandler
from ...core.protocol import (
    BinaryMessageType, Message, MessageType,
    pack_binary,
)
from ...core.session import Monitor

if TYPE_CHECKING:
    from ...core.config import Config
    from ...core.session import Session
    from ...core.transport import Connection

log = logging.getLogger(__name__)


class ScreenCaptureFeature(FeatureHandler):
    handles = frozenset({MessageType.MONITOR_SELECT})

    def __init__(self, cfg: "Config") -> None:
        self._cfg = cfg
        self._task: asyncio.Task | None = None

    async def on_connect(self, session: "Session", transport: "Connection") -> None:
        monitors = self._enumerate_monitors()
        session.monitors = monitors
        session.selected_monitor = self._cfg.screen.monitor_index

        await transport.send_message(Message(
            MessageType.MONITOR_LIST,
            {"monitors": [m.to_dict() for m in monitors]},
        ))

        self._task = asyncio.create_task(
            self._capture_loop(session, transport),
            name="screen_capture",
        )

    async def on_disconnect(self, session: "Session") -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    async def handle(self, session: "Session", transport: "Connection", msg) -> None:
        monitor_id = msg.payload.get("monitor_id", 0)
        valid_ids = {m.id for m in session.monitors}
        if monitor_id not in valid_ids:
            log.warning("Invalid monitor_id %d requested", monitor_id)
            return
        session.selected_monitor = monitor_id
        log.info("Switched to monitor %d", monitor_id)

        if self._task:
            self._task.cancel()
        self._task = asyncio.create_task(
            self._capture_loop(session, transport),
            name="screen_capture",
        )

    async def _capture_loop(self, session: "Session", transport: "Connection") -> None:
        delay = 1.0 / self._cfg.screen.fps

        try:
            while True:
                start = time.monotonic()
                frame = self._grab(session)
                await transport.send_binary(pack_binary(BinaryMessageType.FRAME, frame))
                elapsed = time.monotonic() - start
                await asyncio.sleep(max(0.0, delay - elapsed))
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("Screen capture error")

    def _grab(self, session: "Session") -> bytes:
        with mss.mss() as sct:
            monitors = sct.monitors
            # monitors[0] is virtual "all screens", monitors[1..] are real
            idx = session.selected_monitor + 1 if session.selected_monitor + 1 < len(monitors) else 1
            raw = sct.grab(monitors[idx])
            img = Image.frombytes("RGB", raw.size, raw.rgb)

            native = img.size                       # (w, h) in native pixels
            out_size = self._target_size(native)
            if out_size != native:
                img = img.resize(out_size, Image.BILINEAR)

            # Record sizes so InputFeature can map clicks back to real pixels.
            session.frame_native = native
            session.frame_sent = out_size

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=self._cfg.screen.jpeg_quality)
            return buf.getvalue()

    def _target_size(self, native: tuple[int, int]) -> tuple[int, int]:
        mode = self._cfg.screen.scale_mode
        if mode == "off":
            return native
        tw, th = self._cfg.screen.target_width, self._cfg.screen.target_height
        nw, nh = native
        if nw <= 0 or nh <= 0:
            return native
        if mode == "stretch":
            return (tw, th)
        # "fit": preserve aspect, scale to fit the target box (up or down)
        scale = min(tw / nw, th / nh)
        return (max(1, round(nw * scale)), max(1, round(nh * scale)))

    @staticmethod
    def _enumerate_monitors() -> list[Monitor]:
        with mss.mss() as sct:
            result = []
            for i, m in enumerate(sct.monitors[1:]):  # skip index 0 (all screens)
                result.append(Monitor(
                    id=i,
                    x=m["left"],
                    y=m["top"],
                    width=m["width"],
                    height=m["height"],
                    name=f"Display {i + 1}",
                ))
            return result
