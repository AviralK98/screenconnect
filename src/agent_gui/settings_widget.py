"""Tabbed settings form embedded in the agent window."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton,
    QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt

from ..core.config import Config


class SettingsWidget(QWidget):
    def __init__(self, cfg: Config, parent=None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(self._server_tab(), "Server")
        tabs.addTab(self._auth_tab(), "Auth")
        tabs.addTab(self._screen_tab(), "Screen")
        tabs.addTab(self._tls_tab(), "TLS")
        layout.addWidget(tabs)

        save_btn = QPushButton("Apply")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

        self.load()

    # ── Tabs ──────────────────────────────────────────────────────────────

    def _server_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self._host = QLineEdit()
        self._host.setPlaceholderText("0.0.0.0  (all interfaces — recommended)")
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        f.addRow("Bind host:", self._host)

        host_hint = QLabel(
            "Leave as 0.0.0.0 to listen on every network interface. Don't put "
            "your own LAN IP here — pinning to one adapter can make the agent "
            "unreachable from phones/other devices (e.g. behind a VPN)."
        )
        host_hint.setWordWrap(True)
        host_hint.setStyleSheet("color: #888; font-size: 11px;")
        f.addRow("", host_hint)

        f.addRow("Port:", self._port)
        return w

    def _auth_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        mode_box = QGroupBox("Auth mode")
        mode_layout = QHBoxLayout(mode_box)
        self._rb_token = QRadioButton("Shared token")
        self._rb_users = QRadioButton("User accounts")
        mode_layout.addWidget(self._rb_token)
        mode_layout.addWidget(self._rb_users)
        layout.addWidget(mode_box)

        cred_form = QFormLayout()
        self._token = QLineEdit()
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        cred_form.addRow("Token:", self._token)
        layout.addLayout(cred_form)

        note = QLabel("For user accounts: run  python -m src.accounts.manage adduser <name>")
        note.setWordWrap(True)
        note.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(note)
        layout.addStretch()

        self._rb_token.toggled.connect(lambda on: self._token.setEnabled(on))
        return w

    def _screen_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self._fps = QSpinBox()
        self._fps.setRange(1, 60)
        f.addRow("Frame rate (fps):", self._fps)

        self._quality = QSpinBox()
        self._quality.setRange(1, 100)
        self._quality.setSuffix("%")
        f.addRow("JPEG quality:", self._quality)

        self._monitor_idx = QSpinBox()
        self._monitor_idx.setRange(0, 7)
        self._monitor_idx.setSpecialValueText("Primary (0)")
        f.addRow("Default monitor:", self._monitor_idx)
        return w

    def _tls_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self._tls_enabled = QCheckBox("Enable TLS")
        f.addRow(self._tls_enabled)
        self._tls_cert = QLineEdit()
        self._tls_key  = QLineEdit()
        f.addRow("Cert file:", self._tls_cert)
        f.addRow("Key file:",  self._tls_key)
        note = QLabel("If cert/key don't exist they are auto-generated on first start.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #888; font-size: 11px;")
        f.addRow(note)
        return w

    # ── Load / save ───────────────────────────────────────────────────────

    def load(self) -> None:
        self._host.setText(self._cfg.server.host or "0.0.0.0")
        self._port.setValue(self._cfg.server.port)

        if self._cfg.auth.mode == "users":
            self._rb_users.setChecked(True)
        else:
            self._rb_token.setChecked(True)
        self._token.setText(self._cfg.auth.token)

        self._fps.setValue(self._cfg.screen.fps)
        self._quality.setValue(self._cfg.screen.jpeg_quality)
        self._monitor_idx.setValue(self._cfg.screen.monitor_index)

        self._tls_enabled.setChecked(self._cfg.tls.enabled)
        self._tls_cert.setText(self._cfg.tls.cert_file)
        self._tls_key.setText(self._cfg.tls.key_file)

    def save(self) -> None:
        # An empty host means "all interfaces"; never leave it blank.
        self._cfg.server.host = self._host.text().strip() or "0.0.0.0"
        self._cfg.server.port = self._port.value()

        self._cfg.auth.mode  = "users" if self._rb_users.isChecked() else "token"
        self._cfg.auth.token = self._token.text().strip()

        self._cfg.screen.fps           = self._fps.value()
        self._cfg.screen.jpeg_quality  = self._quality.value()
        self._cfg.screen.monitor_index = self._monitor_idx.value()

        self._cfg.tls.enabled   = self._tls_enabled.isChecked()
        self._cfg.tls.cert_file = self._tls_cert.text().strip()
        self._cfg.tls.key_file  = self._tls_key.text().strip()
