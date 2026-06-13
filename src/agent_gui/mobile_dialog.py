"""Dialog that enables the mobile web viewer and shows how to connect.

Displays the URL to open on a phone, a scannable QR code (if the optional
``qrcode`` package is installed), and the access token reminder.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

from ..core.config import Config
from ..agent.web_server import local_ip


class MobileViewerDialog(QDialog):
    def __init__(self, cfg: Config, window, parent=None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._window = window   # AgentWindow: owns the WebViewerServer

        self.setWindowTitle("Mobile Web Viewer")
        self.setMinimumWidth(380)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        intro = QLabel(
            "Control this machine from your phone's web browser — no app to "
            "install. Connect both devices to the same network."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#aaa;")
        layout.addWidget(intro)

        self._chk = QCheckBox("Enable mobile web viewer")
        self._chk.toggled.connect(self._on_toggle)
        layout.addWidget(self._chk)

        # Connection details card
        card = QFrame()
        card.setStyleSheet("QFrame { background:#1e1e1e; border-radius:8px; }")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(16, 16, 16, 16)
        card_l.setSpacing(10)

        self._lbl_url = QLabel()
        self._lbl_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._lbl_url.setStyleSheet("font-size:17px; font-weight:bold; color:#5a9cff;")
        card_l.addWidget(self._lbl_url)

        hint = QLabel("Open this address in Safari / Chrome on your phone.")
        hint.setStyleSheet("color:#888; font-size:12px;")
        card_l.addWidget(hint)

        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_l.addWidget(self._qr_label)

        self._lbl_token = QLabel()
        self._lbl_token.setWordWrap(True)
        self._lbl_token.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._lbl_token.setStyleSheet("color:#ccc; font-size:12px;")
        card_l.addWidget(self._lbl_token)

        layout.addWidget(card)
        self._card = card

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    # ── State ────────────────────────────────────────────────────────────────

    def _on_toggle(self, on: bool) -> None:
        if on:
            self._window.start_web_viewer()
        else:
            self._window.stop_web_viewer()
        self._refresh()

    def _refresh(self) -> None:
        running = self._window.web_viewer_running()
        self._chk.blockSignals(True)
        self._chk.setChecked(running)
        self._chk.blockSignals(False)
        self._card.setVisible(running)

        if not running:
            self.adjustSize()
            return

        ip = local_ip()
        port = self._cfg.server.web_port
        url = f"http://{ip}:{port}"
        self._lbl_url.setText(url)

        if self._cfg.auth.mode == "users":
            self._lbl_token.setText("Sign in with your username and password.")
        else:
            self._lbl_token.setText(f"Access token:  {self._cfg.auth.token}")

        self._set_qr(url)
        self.adjustSize()

    def _set_qr(self, url: str) -> None:
        pix = _make_qr_pixmap(url)
        if pix is not None:
            self._qr_label.setPixmap(pix)
            self._qr_label.show()
        else:
            self._qr_label.setText("(install 'qrcode' for a scannable code)")
            self._qr_label.setStyleSheet("color:#666; font-size:11px;")


def _make_qr_pixmap(url: str, size: int = 200) -> QPixmap | None:
    """Render a QR code for the URL, or None if qrcode isn't installed."""
    try:
        import qrcode
    except ImportError:
        return None
    try:
        from io import BytesIO
        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        pix = QPixmap()
        pix.loadFromData(buf.getvalue(), "PNG")
        return pix.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    except Exception:
        return None
