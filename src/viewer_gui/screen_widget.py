"""Central widget: renders remote frames and captures mouse/keyboard input."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import (
    QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap, QWheelEvent,
)
from PyQt6.QtWidgets import QWidget

from ..core.protocol import MessageType

# Qt modifier → protocol modifier name
_QT_MOD_MAP = {
    Qt.KeyboardModifier.ControlModifier: "ctrl",
    Qt.KeyboardModifier.MetaModifier:    "cmd",   # Cmd on macOS
    Qt.KeyboardModifier.AltModifier:     "alt",
    Qt.KeyboardModifier.ShiftModifier:   "shift",
}

# Qt key codes → protocol key names
_QT_KEY_MAP = {
    Qt.Key.Key_Return:    "enter",
    Qt.Key.Key_Enter:     "enter",
    Qt.Key.Key_Escape:    "esc",
    Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Tab:       "tab",
    Qt.Key.Key_Space:     "space",
    Qt.Key.Key_Left:      "left",
    Qt.Key.Key_Right:     "right",
    Qt.Key.Key_Up:        "up",
    Qt.Key.Key_Down:      "down",
    Qt.Key.Key_Delete:    "delete",
    Qt.Key.Key_Home:      "home",
    Qt.Key.Key_End:       "end",
    Qt.Key.Key_PageUp:    "page_up",
    Qt.Key.Key_PageDown:  "page_down",
    Qt.Key.Key_F1:  "f1",  Qt.Key.Key_F2:  "f2",  Qt.Key.Key_F3:  "f3",
    Qt.Key.Key_F4:  "f4",  Qt.Key.Key_F5:  "f5",  Qt.Key.Key_F6:  "f6",
    Qt.Key.Key_F7:  "f7",  Qt.Key.Key_F8:  "f8",  Qt.Key.Key_F9:  "f9",
    Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
}

_MODIFIER_KEYS = {
    Qt.Key.Key_Control, Qt.Key.Key_Meta, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
}


class ScreenWidget(QWidget):
    """Displays the remote screen stream and forwards user input."""

    def __init__(self, send_input_cb, parent=None) -> None:
        super().__init__(parent)
        self._send = send_input_cb   # callable(event_dict)
        self._pixmap: QPixmap | None = None
        self._remote_w: int = 1920
        self._remote_h: int = 1080
        self._render_rect = (0, 0, 1, 1)   # x, y, w, h of drawn pixmap

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background-color: #1a1a1a;")

    # ── Frame rendering ────────────────────────────────────────────────────

    def update_frame(self, jpeg_bytes: bytes) -> None:
        img = QImage.fromData(jpeg_bytes)
        if img.isNull():
            return
        self._remote_w = img.width()
        self._remote_h = img.height()
        self._pixmap = QPixmap.fromImage(img)
        self.update()

    def paintEvent(self, event) -> None:
        if self._pixmap is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width()  - scaled.width())  // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        self._render_rect = (x, y, scaled.width(), scaled.height())

    # ── Coordinate mapping ─────────────────────────────────────────────────

    def _to_remote(self, pos: QPoint) -> tuple[int, int]:
        rx, ry, rw, rh = self._render_rect
        if rw == 0 or rh == 0:
            return 0, 0
        x = int((pos.x() - rx) / rw * self._remote_w)
        y = int((pos.y() - ry) / rh * self._remote_h)
        x = max(0, min(x, self._remote_w - 1))
        y = max(0, min(y, self._remote_h - 1))
        return x, y

    # ── Mouse events ───────────────────────────────────────────────────────

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = self._to_remote(event.pos())
        self._send({"type": MessageType.MOUSE_MOVE.value, "x": x, "y": y})

    def mousePressEvent(self, event: QMouseEvent) -> None:
        x, y = self._to_remote(event.pos())
        btn = self._qt_button(event.button())
        if btn:
            self._send({"type": MessageType.MOUSE_CLICK.value,
                        "button": btn, "action": "click", "x": x, "y": y})

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        x, y = self._to_remote(event.pos())
        btn = self._qt_button(event.button())
        if btn:
            self._send({"type": MessageType.MOUSE_CLICK.value,
                        "button": btn, "action": "click", "x": x, "y": y})
            self._send({"type": MessageType.MOUSE_CLICK.value,
                        "button": btn, "action": "click", "x": x, "y": y})

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta()
        dx = 1 if delta.x() > 0 else (-1 if delta.x() < 0 else 0)
        dy = 1 if delta.y() > 0 else (-1 if delta.y() < 0 else 0)
        self._send({"type": MessageType.MOUSE_SCROLL.value, "dx": dx, "dy": dy})

    @staticmethod
    def _qt_button(btn) -> str | None:
        mapping = {
            Qt.MouseButton.LeftButton:   "left",
            Qt.MouseButton.RightButton:  "right",
            Qt.MouseButton.MiddleButton: "middle",
        }
        return mapping.get(btn)

    # ── Keyboard events ────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return
        key = Qt.Key(event.key())

        if key in _MODIFIER_KEYS:
            mod_name = self._qt_key_to_mod(key)
            if mod_name:
                self._send({"type": MessageType.KEY.value,
                            "key": mod_name, "modifiers": [], "action": "down"})
            return

        key_name = _QT_KEY_MAP.get(key)
        if key_name is None:
            text = event.text()
            key_name = text if text else None
        if key_name is None:
            return

        modifiers = self._active_modifiers(event.modifiers())
        self._send({"type": MessageType.KEY.value,
                    "key": key_name, "modifiers": modifiers, "action": "press"})

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            return
        key = Qt.Key(event.key())
        if key in _MODIFIER_KEYS:
            mod_name = self._qt_key_to_mod(key)
            if mod_name:
                self._send({"type": MessageType.KEY.value,
                            "key": mod_name, "modifiers": [], "action": "up"})

    @staticmethod
    def _active_modifiers(mods) -> list[str]:
        result = []
        for qt_mod, name in _QT_MOD_MAP.items():
            if mods & qt_mod:
                result.append(name)
        return result

    @staticmethod
    def _qt_key_to_mod(key) -> str | None:
        return {
            Qt.Key.Key_Control: "ctrl",
            Qt.Key.Key_Meta:    "cmd",
            Qt.Key.Key_Alt:     "alt",
            Qt.Key.Key_Shift:   "shift",
        }.get(key)
