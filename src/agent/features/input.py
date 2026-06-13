from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Key

from ...core.feature import FeatureHandler
from ...core.protocol import MessageType
from ...core import permissions

if TYPE_CHECKING:
    from ...core.session import Session
    from ...core.transport import Connection

log = logging.getLogger(__name__)

_IS_MAC = sys.platform == "darwin"

MODIFIER_MAP: dict[str, Key] = {
    "ctrl":  Key.ctrl,
    "shift": Key.shift,
    "alt":   Key.alt,
    "cmd":   Key.cmd if _IS_MAC else Key.ctrl,
    "super": Key.cmd if _IS_MAC else Key.ctrl,
}

SPECIAL_KEY_MAP: dict[str, Key] = {
    "enter":     Key.enter,
    "return":    Key.enter,
    "esc":       Key.esc,
    "escape":    Key.esc,
    "backspace": Key.backspace,
    "tab":       Key.tab,
    "space":     Key.space,
    "up":        Key.up,
    "down":      Key.down,
    "left":      Key.left,
    "right":     Key.right,
    "delete":    Key.delete,
    "home":      Key.home,
    "end":       Key.end,
    "page_up":   Key.page_up,
    "page_down": Key.page_down,
    "f1":  Key.f1,  "f2":  Key.f2,  "f3":  Key.f3,  "f4":  Key.f4,
    "f5":  Key.f5,  "f6":  Key.f6,  "f7":  Key.f7,  "f8":  Key.f8,
    "f9":  Key.f9,  "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
}


class InputFeature(FeatureHandler):
    handles = frozenset({
        MessageType.MOUSE_MOVE,
        MessageType.MOUSE_CLICK,
        MessageType.MOUSE_SCROLL,
        MessageType.KEY,
    })

    def __init__(self) -> None:
        self._mouse = MouseController()
        self._keyboard = KeyboardController()
        # Tracks the last-known control-permission state so we only log
        # the transition once, not on every dropped event.
        self._control_allowed: bool | None = None
        # Optional callback(bool) invoked when the permission state flips.
        self.on_control_state_changed: Callable[[bool], None] | None = None

    def _check_control(self) -> bool:
        """Return whether input injection is permitted, logging transitions."""
        allowed = permissions.control_granted()
        if allowed != self._control_allowed:
            self._control_allowed = allowed
            if allowed:
                log.info("Remote control permission granted — input enabled.")
            else:
                log.warning(
                    "Remote control blocked: Accessibility permission not granted. "
                    "Grant it in System Settings → Privacy & Security → Accessibility."
                )
            if self.on_control_state_changed:
                try:
                    self.on_control_state_changed(allowed)
                except Exception:
                    pass
        return allowed

    async def handle(self, session: "Session", transport: "Connection", msg) -> None:
        # Gate every input event on the OS control permission. Until it is
        # granted, incoming mouse/keyboard events are dropped rather than
        # silently failing at the pynput layer.
        if not self._check_control():
            return

        t = msg.type

        if t == MessageType.MOUSE_MOVE:
            self._mouse.position = (int(msg.payload["x"]), int(msg.payload["y"]))

        elif t == MessageType.MOUSE_CLICK:
            btn_name = msg.payload.get("button", "left")
            button = {
                "left":   Button.left,
                "right":  Button.right,
                "middle": Button.middle,
            }.get(btn_name, Button.left)
            action = msg.payload.get("action", "click")
            self._mouse.position = (int(msg.payload["x"]), int(msg.payload["y"]))
            if action == "click":
                self._mouse.click(button)
            elif action == "down":
                self._mouse.press(button)
            elif action == "up":
                self._mouse.release(button)

        elif t == MessageType.MOUSE_SCROLL:
            self._mouse.scroll(int(msg.payload.get("dx", 0)), int(msg.payload.get("dy", 0)))

        elif t == MessageType.KEY:
            self._dispatch_key(msg.payload)

    def _dispatch_key(self, payload: dict) -> None:
        key_name = payload.get("key", "")
        modifiers = [m.lower() for m in payload.get("modifiers", [])]
        action = payload.get("action", "press")

        # If the key itself is a modifier (for sticky mod down/up events)
        if key_name.lower() in MODIFIER_MAP:
            k = MODIFIER_MAP[key_name.lower()]
            if action == "down":
                self._keyboard.press(k)
            elif action == "up":
                self._keyboard.release(k)
            return

        k = SPECIAL_KEY_MAP.get(key_name.lower(), key_name)

        pressed_mods: list[Key] = []
        for mod_name in modifiers:
            mod_key = MODIFIER_MAP.get(mod_name)
            if mod_key:
                self._keyboard.press(mod_key)
                pressed_mods.append(mod_key)

        try:
            if action in ("press", "click"):
                self._keyboard.press(k)
                self._keyboard.release(k)
            elif action == "down":
                self._keyboard.press(k)
            elif action == "up":
                self._keyboard.release(k)
        except Exception as e:
            log.warning("Key dispatch error for %r: %s", key_name, e)
        finally:
            for mod_key in reversed(pressed_mods):
                self._keyboard.release(mod_key)
