from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import cv2

from ...core.feature import FeatureHandler
from ...core.protocol import Message, MessageType

if TYPE_CHECKING:
    from ...core.session import Session
    from ...core.transport import Connection

log = logging.getLogger(__name__)

WINDOW = "ScreenConnect"

# cv2 extended key flag bits
_CV2_FLAG_CTRL  = 0x08
_CV2_FLAG_SHIFT = 0x10
_CV2_FLAG_ALT   = 0x20

# Keys that are modifier keys themselves (cv2 extended codes)
_MODIFIER_KEYS = {
    0x11: "ctrl",    # VK_CONTROL
    0x10: "shift",   # VK_SHIFT
    0x12: "alt",     # VK_MENU
}


class InputCaptureFeature(FeatureHandler):
    handles = frozenset()   # sends events; doesn't receive them

    def __init__(self, display_feature, clipboard_feature=None, monitor_cycle_cb=None) -> None:
        self._display = display_feature
        self._clipboard = clipboard_feature
        self._monitor_cycle_cb = monitor_cycle_cb
        self._transport: "Connection | None" = None
        self._session: "Session | None" = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._held_modifiers: set[str] = set()
        self._task: asyncio.Task | None = None

    async def on_connect(self, session: "Session", transport: "Connection") -> None:
        self._transport = transport
        self._session = session
        self._held_modifiers.clear()

        loop = asyncio.get_running_loop()
        cv2.setMouseCallback(WINDOW, self._mouse_callback, loop)

        self._task = asyncio.create_task(self._event_sender(), name="input_sender")
        asyncio.create_task(self._key_poll_loop(), name="key_poll")

    async def on_disconnect(self, session: "Session") -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        self._transport = None

    # ------------------------------------------------------------------ #
    # Key polling — cv2 doesn't have async key events, so we poll         #
    # ------------------------------------------------------------------ #

    async def _key_poll_loop(self) -> None:
        try:
            while self._transport is not None:
                key = self._display.poll_window_events()
                if key == 255:  # no key
                    await asyncio.sleep(0.01)
                    continue
                await self._handle_cv2_key(key)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

    async def _handle_cv2_key(self, key: int) -> None:
        # Escape = disconnect
        if key == 27:
            if self._transport:
                await self._transport.close()
            return

        modifiers = list(self._held_modifiers)

        # Clipboard shortcuts: Ctrl+Shift+C / Ctrl+Shift+V
        if "ctrl" in modifiers and "shift" in modifiers:
            if key == ord("c") or key == ord("C"):
                if self._clipboard:
                    await self._clipboard.pull_clipboard(self._transport)
                return
            if key == ord("v") or key == ord("V"):
                if self._clipboard:
                    await self._clipboard.push_clipboard(self._transport)
                return

        # Monitor cycle: Ctrl+M
        if "ctrl" in modifiers and (key == ord("m") or key == ord("M")):
            if self._monitor_cycle_cb:
                await self._monitor_cycle_cb(self._session, self._transport)
            return

        # Map cv2 key code to key name
        key_name = self._cv2_key_to_name(key)
        if key_name:
            self._queue.put_nowait({
                "type": MessageType.KEY,
                "key": key_name,
                "modifiers": modifiers,
                "action": "press",
            })

    def _cv2_key_to_name(self, key: int) -> str | None:
        special = {
            13: "enter", 10: "enter",
            8:  "backspace",
            9:  "tab",
            32: "space",
            0x250000: "left",  0x270000: "right",
            0x260000: "up",    0x280000: "down",
            0x2E0000: "delete",
            0x240000: "home",  0x230000: "end",
            0x210000: "page_up", 0x220000: "page_down",
        }
        if key in special:
            return special[key]
        if 32 <= key <= 126:
            return chr(key)
        return None

    # ------------------------------------------------------------------ #
    # Mouse callback (called from cv2 on the main thread)                 #
    # ------------------------------------------------------------------ #

    def _mouse_callback(self, event, x, y, flags, loop: asyncio.AbstractEventLoop) -> None:
        modifiers = list(self._held_modifiers)
        if flags & _CV2_FLAG_CTRL:
            modifiers = list(set(modifiers) | {"ctrl"})
        if flags & _CV2_FLAG_SHIFT:
            modifiers = list(set(modifiers) | {"shift"})
        if flags & _CV2_FLAG_ALT:
            modifiers = list(set(modifiers) | {"alt"})

        if event == cv2.EVENT_MOUSEMOVE:
            loop.call_soon_threadsafe(
                self._queue.put_nowait,
                {"type": MessageType.MOUSE_MOVE, "x": x, "y": y},
            )
        elif event == cv2.EVENT_LBUTTONDOWN:
            loop.call_soon_threadsafe(
                self._queue.put_nowait,
                {"type": MessageType.MOUSE_CLICK, "button": "left", "action": "click", "x": x, "y": y},
            )
        elif event == cv2.EVENT_RBUTTONDOWN:
            loop.call_soon_threadsafe(
                self._queue.put_nowait,
                {"type": MessageType.MOUSE_CLICK, "button": "right", "action": "click", "x": x, "y": y},
            )
        elif event == cv2.EVENT_MBUTTONDOWN:
            loop.call_soon_threadsafe(
                self._queue.put_nowait,
                {"type": MessageType.MOUSE_CLICK, "button": "middle", "action": "click", "x": x, "y": y},
            )
        elif event == cv2.EVENT_MOUSEWHEEL:
            dy = 1 if flags > 0 else -1
            loop.call_soon_threadsafe(
                self._queue.put_nowait,
                {"type": MessageType.MOUSE_SCROLL, "dx": 0, "dy": dy},
            )

    # ------------------------------------------------------------------ #
    # Sender coroutine — drains the queue onto the WebSocket              #
    # ------------------------------------------------------------------ #

    async def _event_sender(self) -> None:
        try:
            while True:
                event = await self._queue.get()
                if self._transport is None:
                    continue
                msg_type = event.pop("type")
                await self._transport.send_message(Message(msg_type, event))
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("Input sender error")
